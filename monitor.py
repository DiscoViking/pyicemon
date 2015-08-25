# Monitor an icecream server.
from __future__ import print_function

import sys
import logging

import messages
from connection import Connection
from publisher import Publisher

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class CS(object):
    def __init__(self, id, name, ip, maxjobs):
        self.id = id
        self.name = name
        self.ip = ip
        self.maxjobs = maxjobs
        self.active_jobs = 0

    def __str__(self):
        return "[CS {c.id}] {c.name} : {c.ip}".format(c=self)


class Job(object):
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
    def __init__(self, host, port=8765):
        self.socket = None
        self.server_host = host
        self.server_port = port
        self.conn = Connection(host, port)
        self.conn.send_message(messages.LoginMessage())

        self.cs = {}
        self.jobs = {}

        self.pub = Publisher()

    def run(self):
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

            self.pub.publish(self)

    def handleStats(self, msg):
        if ("State" in msg.data and msg.data["State"] == "Offline"):
            # Destroy this CS if we have it.
            if msg.host_id in self.cs.iterkeys():
                log.info(
                    "({0}) went offline.".format(self.cs[msg.host_id]))
                del self.cs[msg.host_id]
            return

        # Updating/Creating a CS.
        name = msg.data["Name"]
        ip = msg.data["IP"]
        maxjobs = int(msg.data["MaxJobs"])
        cs = CS(msg.host_id, name, ip, maxjobs)

        if msg.host_id not in self.cs.iterkeys():
            log.info("New CS ({0}) came online.".format(cs))

        self.cs[msg.host_id] = cs

    def handleGetCS(self, msg):
        job = Job(msg.job_id, msg.filename, msg.client_id)
        log.info("New job {0}".format(job))
        self.jobs[job.id] = job

    def handleJobBegin(self, msg):
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
        job = Job(msg.job_id, msg.filename, msg.client_id, local=True)
        job.host_id = msg.client_id
        log.info("Created local job: {0}".format(job))
        self.jobs[job.id] = job

        if job.host_id in self.cs:
            self.cs[job.client_id].active_jobs += 1

    def handleLocalJobDone(self, msg):
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
    mon.run()
