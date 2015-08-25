import struct
from collections import OrderedDict

# Abstract message base class.
class Message(object):
    byte_format = ""

    @classmethod
    def unpack_string(cls, s):
        length = struct.unpack("!L", s[:4])[0]
        string = s[4:length + 4 - 1]
        s = s[length + 4:]
        return string, s


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

    def __init__(self, host_id, body):
        self.host_id = host_id
        self.parse_body(body)

    def parse_body(self, body):
        self.data = OrderedDict()
        for l in body.split("\n"):
            vals = l.split(":")
            if len(vals) == 2:
                self.data[vals[0]] = vals[1]

    def pack(self):
        body = "\n".join(":".join(i) for i in self.data.iteritems())
        return (
            struct.pack(self.byte_format,
                        self.host_id,
                        len(body)) +
            self.body +
            "\x00"
        )

    @classmethod
    def unpack(cls, string):
        (host_id) = struct.unpack("!L", string[:4])

        body, remainder = cls.unpack_string(string[4:])
        assert(not remainder)
        return StatsMessage(host_id, body)

    def __str__(self):
        body = "\n".join(": ".join(i) for i in self.data.iteritems())
        return "[STATS] host = {0}, \n{1}".format(self.host_id, body)


# Local Job Begin message.
# Send Scheduler -> Monitor to report start of a local job.
# Format is <job_id><time><host_id>[filename]
class LocalJobBeginMessage(Message):
    byte_format = "!LLL"
    msg_type = 0x57

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

        filename, remainder = cls.unpack_string(string[hdr_len:])
        assert(not remainder)

        return LocalJobBeginMessage(job_id, time, host_id, filename)

    def __str__(self):
        return "[LOCAL JOB BEGIN] id = {0}, host = {1}, time = {2}\n{3}".format(
            self.job_id, self.host_id, self.time, self.filename)


# GetCS message.
class GetCSMessage(Message):
    msg_type = 0x53

    def __init__(self, filename, lang, job_id, client_id):
        self.filename = filename
        self.lang = lang
        self.job_id = job_id
        self.client_id = client_id

    def pack(self):
        return (
            self.filename + "\x00" +
            struct.pack("!LLL", self.lang, self.job_id, self.client_id)
        )

    @classmethod
    def unpack(cls, string):
        filename, string = cls.unpack_string(string)
        print(filename, ":".join(c for c in string))

        (lang,
         job_id,
         client_id) = struct.unpack("!LLL", string)

        return GetCSMessage(filename, lang, job_id, client_id)

    def __str__(self):
        return "[GetCS] lang = {0}, job_id = {1}, client_id = {2}\n{3}".format(
            self.lang, self.job_id, self.client_id, self.filename)
