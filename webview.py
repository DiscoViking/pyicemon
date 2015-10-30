"""Main module for pyicemon webview"""

import SimpleHTTPServer
import SocketServer
import threading
import sys
import os
import logging
from monitor import Monitor
from publishers import WebsocketPublisher
from connection import Connection

PORT = 80

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARN, filename="pyicemon.log")

    # Serve static HTTP content.
    os.chdir("static")
    handler = SimpleHTTPServer.SimpleHTTPRequestHandler
    httpd = SocketServer.TCPServer(("", PORT), handler)
    t = threading.Thread(target=httpd.serve_forever)
    t.daemon = True
    t.start()

    # Fire up pyicemon.
    host, port = sys.argv[1], sys.argv[2]
    mon = Monitor(Connection(host, int(port)))
    mon.addPublisher(WebsocketPublisher(port=9999))
    mon.run()
