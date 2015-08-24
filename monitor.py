# Monitor an icecream server.
from __future__ import print_function

import socket
import sys
import messages
import struct
import logging

log = logging.getLogger("monitor")
log.addHandler(logging.NullHandler())
logging.basicConfig()


class Monitor(object):
    msg_types = {
        0x52: messages.LoginMessage,
        0x56: messages.LocalJobBeginMessage,
        0x57: messages.StatsMessage,
    }

    CHUNK_SIZE = 2048
    input_buf = ""

    def __init__(self):
        self.socket = None
        self.server_host = ""
        self.server_port = 0

    def connect(self, host, port):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((host, port))
        self.server_host = host
        self.server_port = port

    def send(self, msg):
        print("Sending:\n{0}".format(':'.join(x.encode('hex') for x in msg)))
        totalsent = 0
        while totalsent < len(msg):
            sent = self.socket.send(msg[totalsent:])
            if sent == 0:
                return
            totalsent += sent

    def recv_chunk(self):
        msg = self.socket.recv(self.CHUNK_SIZE)
        self.input_buf += msg
        return len(msg)

    def receive(self, n):
        while len(self.input_buf) < n:
            self.recv_chunk()
        s, self.input_buf = self.input_buf[:n], self.input_buf[n:]
        print("Received:\n{0}".format(':'.join(x.encode('hex') for x in s)))
        return s

    def receive_until_null(self):
        i = 0
        while True:
            if i < len(self.input_buf) and self.input_buf[i] == '\x00':
                break

            i += 1
            if i >= len(self.input_buf):
                amount_read = 0
                while amount_read == 0:
                    amount_read = self.recv_chunk()
                    log.info("Read {0} bytes.".format(amount_read))

        s, self.input_buf = self.input_buf[:i+1], self.input_buf[i+1:]
        return s

    def get_message(self):
        common = self.receive(8)
        assert(len(common) == 8)

        (host_id, msg_type) = struct.unpack("!LL", common)
        if msg_type not in self.msg_types:
            log.error("Unknown message type: {0}".format(msg_type))

        msg_cls = self.msg_types[msg_type]
        header = self.receive(msg_cls.hdr_len())
        assert(len(header) == msg_cls.hdr_len())

        body = ""
        if msg_cls.has_body:
            body = self.receive_until_null()

        print("Received message of length: {0}".format(len(common) +
                                                          len(header) +
                                                          len(body)))

        return msg_cls.unpack(common + header + body)


if __name__ == "__main__":
    host, port = sys.argv[1], sys.argv[2]
    mon = Monitor()
    mon.connect(host, int(port))

    # Protocol Negotiation
    mon.send("\x1d\x00\x00\x00")
    mon.receive(4)
    mon.send("\x1d\x00\x00\x00")
    mon.receive(4)

    # Login
    #mon.send("\x00\x00\x00\x04\x00\x00\x00\x52")
    mon.send(messages.LoginMessage(4).pack())
    while True:
        msg = mon.get_message()
        print(msg)
