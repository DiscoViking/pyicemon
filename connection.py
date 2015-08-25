import socket
import messages
import struct
import logging

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class Connection(object):
    """Represents a connection to a icecream scheduler."""
    CHUNK_SIZE = 2048

    def __init__(self, host, port=8765):
        self.socket = None
        self.server_host = host
        self.server_port = port
        self.input_buf = ""
        self.connect()

    def connect(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.server_host, self.server_port))
        log.debug("Sending protocol version 22")
        self.socket.send("\x22\x00\x00\x00")
        log.debug("Receiving protocol version")
        assert(self.socket.recv(4) == "\x22\x00\x00\x00")
        log.debug("Sending protocol version 22")
        self.socket.send("\x22\x00\x00\x00")
        log.debug("Receiving protocol version")
        assert(self.socket.recv(4) == "\x22\x00\x00\x00")

    def send(self, s):
        log.debug("Sending:\n{0}".format(':'.join(x.encode('hex') for x in s)))
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
        log.debug("Received:\n{0}".format(':'.join(x.encode('hex') for x in s)))
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
        length = struct.unpack("!L", self.receive(4))[0]

        log.debug("Receiving message of length {0}".format(length))

        msg = self.receive(length)

        return messages.unpack(msg)
