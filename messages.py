import struct
from collections import OrderedDict

# Abstract message base class.
class Message(object):
    byte_format = ""
    has_body = False


# Login message.
# Send Monitor -> Scheduler to register for notifications.
# Format is <host_id><msg_type>
class LoginMessage(Message):
    msg_type = 0x52

    def pack(self):
        return ""

    @classmethod
    def unpack(cls, string):
        return LoginMessage()

    def __str__(self):
        return "[LOGIN]"


# Stats message.
# Send Scheduler -> Monitor to report detailed info for one CS.
# Format is <host_id><msg_type><value1><value2>[body]
# Note:  Still don't know what value1/2 mean.
class StatsMessage(Message):
    byte_format = "!LL"
    has_body = True

    def __init__(self, host_id, value2, body):
        self.host_id = host_id
        self.value2 = value2
        self.parse_body(body)

    def parse_body(self, body):
        self.data = OrderedDict()
        for l in body.split("\n"):
            vals = l.split(":")
            if len(vals) == 2:
                self.data[vals[0]] = vals[1]

    def pack(self):
        return (
            struct.pack(self.byte_format,
                        self.host_id,
                        self.value2) +
            "\n".join(":".join(i) for i in self.data.iteritems()) +
            "\x00"
        )

    @classmethod
    def unpack(cls, string):
        hdr_len = struct.calcsize(cls.byte_format)

        (host_id,
         value2) = struct.unpack(cls.byte_format,
                                 string[:hdr_len])

        return StatsMessage(host_id, value2, string[hdr_len:])

    def __str__(self):
        body = "\n".join(": ".join(i) for i in self.data.iteritems())
        return "[STATS] host = {0}, value2 = {1}\n{2}".format(
            self.host_id, self.value2, body)


# Local Job Begin message.
# Send Scheduler -> Monitor to report start of a local job.
# Format is <job_id><msg_type><host_id><time>[filename]
class LocalJobBeginMessage(Message):
    byte_format = "!LLL"
    msg_type = 0x57
    has_body = True
    def __init__(self, job_id, host_id, time, filename):
        self.job_id = job_id
        self.host_id = host_id
        self.time = time
        self.filename = filename

    def pack(self):
        return (
            struct.pack(self.byte_format,
                        self.job_id,
                        self.time,
                        self.host_id) +
            self.filename + "\x00"
        )

    @classmethod
    def unpack(cls, string):
        hdr_len = cls.hdr_len()

        (job_id,
         time,
         host_id) = struct.unpack(cls.byte_format,
                                  string[:hdr_len])

        return LocalJobBeginMessage(job_id, time, host_id, string[hdr_len:])

    def __str__(self):
        return "[LOCAL JOB BEGIN] id = {0}, host = {1}, time = {2}\n{3}".format(
            self.job_id, self.host_id, self.time, self.filename)
