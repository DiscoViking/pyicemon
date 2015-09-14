# Monitor an icecream server.
from __future__ import print_function

import sys
import logging

import messages
from connection import Connection
from publishers import WebsocketPublisher

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class CS(object):
    """Represents one active compilation node."""

    def __init__(self, id, name, ip, maxjobs):
        self.id = id
        self.name = name
        self.ip = ip
        self.maxjobs = maxjobs
        self.active_jobs = 0

    def __str__(self):
        return "[CS {c.id}] {c.name} : {c.ip}".format(c=self)


class Job(object):
    """Represents one active compile Job."""

    def __init__(self, id, filename, client_id, local=False):
        self.id = id
        self.filename = filename
        self.client_id = client_id
        self.host_id = 0
        self.local = local

    def __str__(self):
        return (
            "[Job {j.id}] {j.client_id} -> {j.host_id} : {j.filename}"
        ).format(j=self)


class Monitor(object):
    """
    Monitor for an icecream cluster.

    Owns a connection to the scheduler.
    Maintains an in-memory view of the cluster state which is updated
    in response to notification messages.

    Also may have one or more publishers attached which are notified
    whenever the state of the cluster changes.
    """

    def __init__(self, host, port=8765):
        self.socket = None
        self.server_host = host
        self.server_port = port
        self.conn = Connection(host, port)
        self.conn.send_message(messages.LoginMessage())

        self.cs = {}
        self.jobs = {}

        self.publishers = []

    def addPublisher(self, p):
        """Add the publisher to the monitor."""
        self.publishers.append(p)

    def run(self):
        """Main monitor loop.  Receives and handles messages one at a time."""
        while True:
            msg = self.conn.get_message()

            if isinstance(msg, messages.StatsMessage):
                self.handleStats(msg)
            elif isinstance(msg, messages.GetCSMessage):
                self.handleGetCS(msg)
            elif isinstance(msg, messages.JobBeginMessage):
                self.handleJobBegin(msg)
            elif isinstance(msg, messages.JobDoneMessage):
                self.handleJobDone(msg)
            elif isinstance(msg, messages.LocalJobBeginMessage):
                self.handleLocalJobBegin(msg)
            elif isinstance(msg, messages.LocalJobDoneMessage):
                self.handleLocalJobDone(msg)
            else:
                print("Not handling message:")
                print(msg)
                print("")

            for p in self.publishers:
                p.publish(self)

    def handleStats(self, msg):
        """
        Handle a Stats message.

        Create/Destroy/Update the relevant CS as appropriate.
        """
        if ("State" in msg.data and msg.data["State"] == "Offline"):
            # Destroy this CS if we have it.
            if msg.host_id in self.cs.keys():
                log.info(
                    "({0}) went offline.".format(self.cs[msg.host_id]))
                del self.cs[msg.host_id]
            return

        # Updating/Creating a CS.
        name = msg.data["Name"]
        ip = msg.data["IP"]
        maxjobs = int(msg.data["MaxJobs"])
        cs = CS(msg.host_id, name, ip, maxjobs)

        if msg.host_id not in self.cs.keys():
            log.info("New CS ({0}) came online.".format(cs))

        self.cs[msg.host_id] = cs

    def handleGetCS(self, msg):
        """
        Handle a GetCS message.

        This indicates the beginning of a new compile job, so create
        a new Job to track it.
        """
        job = Job(msg.job_id, msg.filename, msg.client_id)
        log.info("New job {0}".format(job))
        self.jobs[job.id] = job

    def handleJobBegin(self, msg):
        """
        Handle a JobBegin message.

        We should have already created a Job when we got the GetCS message.
        So look it up, and update it with the chosen CS.
        Update the CS's active jobs.
        """
        if msg.job_id not in self.jobs:
            log.warn("JobBegin received for unknown job {0}."
                     .format(msg.job_id))
            return

        job = self.jobs[msg.job_id]
        job.host_id = msg.host_id
        log.info("Updated job: {0}".format(job))

        if job.host_id in self.cs:
            self.cs[job.host_id].active_jobs += 1

    def handleJobDone(self, msg):
        """
        Handle a JobDone message.

        Look up the Job, destroy it, and update the CS's active jobs.
        """
        if msg.job_id not in self.jobs:
            log.warn("JobDone received for unknown job {0}."
                     .format(msg.job_id))
            return

        job = self.jobs[msg.job_id]
        log.info("Deleting job {0}.".format(job))
        del self.jobs[msg.job_id]

        if job.host_id in self.cs:
            self.cs[job.host_id].active_jobs -= 1

    def handleLocalJobBegin(self, msg):
        """
        Handle a LocalJobBegin message.

        This indicates the start of a new local job. (there won't have been
        a GetCS since local jobs don't need to find a remote host.

        So create the new job and update the CS's active jobs.
        """
        job = Job(msg.job_id, msg.filename, msg.client_id, local=True)
        job.host_id = msg.client_id
        log.info("Created local job: {0}".format(job))
        self.jobs[job.id] = job

        if job.host_id in self.cs:
            self.cs[job.client_id].active_jobs += 1

    def handleLocalJobDone(self, msg):
        """
        Handle a LocalJobDone message.

        Look up the Job, destroy it, and update the CS's active jobs.
        """
        if msg.job_id not in self.jobs:
            log.warn("LocalJobDone received for unknown job {0}."
                     .format(msg.job_id))
            return

        job = self.jobs[msg.job_id]
        log.info("Deleting local job {0}.".format(job))
        del self.jobs[msg.job_id]

        if job.host_id in self.cs:
            self.cs[job.client_id].active_jobs -= 1


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARN)

    host, port = sys.argv[1], sys.argv[2]
    mon = Monitor(host, int(port))
    mon.addPublisher(WebsocketPublisher(port=9999))
    mon.run()
