# Monitor an icecream server.
from __future__ import print_function

import socket
import sys
import messages
import struct
import logging

log = logging.getLogger("monitor")
log.addHandler(logging.NullHandler())


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
        log.debug("Sending protocol version 22")
        self.socket.send("\x22\x00\x00\x00")
        log.debug("Receiving protocol version")
        assert(self.socket.recv(4) == "\x22\x00\x00\x00")
        log.debug("Sending protocol version 22")
        self.socket.send("\x22\x00\x00\x00")

    def send(self, s):
        print("Sending:\n{0}".format(':'.join(x.encode('hex') for x in s)))
        totalsent = 0
        while totalsent < len(s):
            sent = self.socket.send(s[totalsent:])
            if sent == 0:
                return
            totalsent += sent

    def send_message(self, msg):
        msg_string = msg.pack()
        self.send(struct.pack("!LL", len(msg_string), msg.msg_type) +
                  msg_string)

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
        length, msg_type = struct.unpack("!LL", self.receive(8))

        log.debug("Receiving message of type {0}, length {1}".format(msg_type,
                                                                     length))

        msg = self.receive(length-4)

        if msg_type not in self.msg_types:
            log.error("Unknown message type: {0}".format(msg_type))

        msg_cls = self.msg_types[msg_type]

        return msg_cls.unpack(msg)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    host, port = sys.argv[1], sys.argv[2]
    mon = Monitor()
    mon.connect(host, int(port))

    # Login
    mon.send_message(messages.LoginMessage())
    mon.receive(4)
    while True:
        msg = mon.get_message()
        print(msg)
