import struct
import logging

from collections import OrderedDict

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class Message(object):
    """Abstract message base class."""

    byte_format = ""

    @classmethod
    def unpack_string(cls, s):
        (length,) = struct.unpack("!L", s[:4])
        string = s[4:length + 4 - 1]
        s = s[length + 4:]
        return string, s


class LoginMessage(Message):
    """
    Sent Monitor -> Scheduler to register for notifications.

    Format is <host_id><msg_type>
    """

    msg_type = 0x52

    def pack(self):
        return b''

    @classmethod
    def unpack(cls, string):
        return LoginMessage()

    def __str__(self):
        return "[LOGIN]"


class StatsMessage(Message):
    """
    Contains detailed information about one CS.

    Format is <host_id>[body]
    """

    msg_type = 0x57

    def __init__(self, host_id, body):
        self.host_id = host_id
        self.parse_body(body)

    def parse_body(self, body):
        self.data = OrderedDict()
        for l in body.split(b'\n'):
            vals = l.split(b':')
            if len(vals) == 2:
                self.data[vals[0].decode()] = vals[1].decode()

    def pack(self):
        body = b'\n'.join(b':'.join(map(lambda s: s.encode(), i)) for i in self.data.items())
        return (
            struct.pack("!LL",
                        self.host_id,
                        len(body)) +
            body +
            b'\x00'
        )

    @classmethod
    def unpack(cls, string):
        (host_id,) = struct.unpack("!L", string[:4])

        body, remainder = cls.unpack_string(string[4:])
        assert(not remainder)
        return StatsMessage(host_id, body)

    def __str__(self):
        body = "\n".join(": ".join(i) for i in self.data.items())
        return "[STATS] host = {0}, \n{1}".format(self.host_id, body)


class LocalJobBeginMessage(Message):
    """
    Indicates a local job (e.g. linking) is starting.

    Format is <client_id><job_id><time>[filename]
    """

    msg_type = 0x56

    def __init__(self, job_id, client_id, time, filename):
        self.job_id = job_id
        self.client_id = client_id
        self.time = time
        self.filename = filename

    def pack(self):
        return (
            struct.pack("!LLLL",
                        self.client_id,
                        self.job_id,
                        self.time,
                        len(self.filename)) +
            self.filename +
            b'\x00'
        )

    @classmethod
    def unpack(cls, string):
        hdr_len = struct.calcsize("!LLL")

        (client_id,
         job_id,
         time) = struct.unpack("!LLL",
                               string[:hdr_len])

        filename, remainder = cls.unpack_string(string[hdr_len:])
        assert(not remainder)

        return LocalJobBeginMessage(job_id, client_id, time, filename)

    def __str__(self):
        return (
            "[LOCAL JOB BEGIN] id = {0}, client = {1}, time = {2}\n{3}"
        ).format(self.job_id, self.client_id, self.time, self.filename)


class LocalJobDoneMessage(Message):
    """
    Indicates that a local job has been completed.

    Format is <job_id>
    """

    msg_type = 0x4f

    def __init__(self, job_id):
        self.job_id = job_id

    def pack(self):
        return struct.pack("!L", self.job_id)

    @classmethod
    def unpack(cls, string):
        (job_id,) = struct.unpack("!L", string)
        return LocalJobDoneMessage(job_id)

    def __str__(self):
        return "[LOCAL JOB DONE] id = {0}".format(self.id)

class GetCSMessage(Message):
    """
    Indicates that a client has requested a CS to build the mentioned file.

    Marks the creation of a new job.
    Format is [filename]<lang><job_id><client_id>
    """

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

        (lang,
         job_id,
         client_id) = struct.unpack("!LLL", string)

        return GetCSMessage(filename, lang, job_id, client_id)

    def __str__(self):
        return "[GetCS] lang = {0}, job_id = {1}, client_id = {2}\n{3}".format(
            self.lang, self.job_id, self.client_id, self.filename)


class JobBeginMessage(Message):
    """
    Indicates that a compile job is starting on a host.

    Format is <job_id><time><host_id>
    """

    msg_type = 0x54

    def __init__(self, job_id, time, host_id):
        self.job_id = job_id
        self.time = time
        self.host_id = host_id

    def pack(self):
        return struct.pack("!LLL", self.job_id, self.time, self.host_id)

    @classmethod
    def unpack(cls, string):
        (job_id,
         time,
         host_id) = struct.unpack("!LLL", string)

        return JobBeginMessage(job_id, time, host_id)

    def __str__(self):
        return "[JobBegin] job_id = {0}, host_id = {1}, time = {2}".format(
            self.job_id, self.host_id, self.time)


class JobDoneMessage(Message):
    """
    Indicates that a compile job is finished.

    Format is <job_id><exit_code><real_ms><user_ms><sys_ms><pfaults>
              <in_compressed><in_uncompressed><out_compressed><out_uncompressed>
              <flags>
    """

    msg_type = 0x55
    byte_format = "!LLLLLLLLLLL"

    def __init__(self, job_id, rc, real_ms, user_ms, sys_ms,
                 pfaults, in_comp, in_uncomp, out_comp, out_uncomp, flags):
        self.job_id = job_id
        self.rc = rc
        self.real_ms = real_ms
        self.user_ms = user_ms
        self.sys_ms = sys_ms
        self.pfaults = pfaults
        self.in_comp = in_comp
        self.in_uncomp = in_uncomp
        self.out_comp = out_comp
        self.out_uncomp = out_uncomp
        self.flags = flags

    def pack(self):
        return struct.pack(self.byte_format, self.job_id, self.rc,
                           self.real_ms, self.user_ms, self.sys_ms,
                           self.pfaults, self.in_comp, self.in_uncomp,
                           self.out_comp, self.out_uncomp, self.flags)

    @classmethod
    def unpack(cls, string):
        (job_id, rc,
         real_ms, user_ms, sys_ms,
         pfaults, in_comp, in_uncomp,
         out_comp, out_uncomp, flags) = struct.unpack(cls.byte_format, string)

        return JobDoneMessage(job_id, rc, real_ms, user_ms, sys_ms,
                              pfaults, in_comp, in_uncomp,
                              out_comp, out_uncomp, flags)

    def __str__(self):
        return (
            "[JobDone] job_id = {m.job_id}, rc = {m.rc}\n"
            "Time: real={m.real_ms}, user={m.user_ms}, sys={m.sys_ms}\n"
        ).format(m=self)


msg_types = {
    LoginMessage.msg_type: LoginMessage,
    StatsMessage.msg_type: StatsMessage,
    LocalJobBeginMessage.msg_type: LocalJobBeginMessage,
    LocalJobDoneMessage.msg_type: LocalJobDoneMessage,
    GetCSMessage.msg_type: GetCSMessage,
    JobBeginMessage.msg_type: JobBeginMessage,
    JobDoneMessage.msg_type: JobDoneMessage,
}


def unpack(s):
    (msg_type,) = struct.unpack("!L", s[:4])
    if msg_type not in msg_types:
        log.warn("Unknown message type {0}. Discarding.".format(msg_type))
        return None

    msg_cls = msg_types[msg_type]
    return msg_cls.unpack(s[4:])
