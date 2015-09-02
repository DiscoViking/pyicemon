import json
import time
import threading
from websocket_server import WebsocketServer


class WebsocketPublisher(object):
    MIN_SEND_GAP_S = 0.1

    def __init__(self, host="0.0.0.0", port=9999):
        self.frame = ""
        self.last_sent_frame = ""
        self.next_time_to_send = 0
        self.lock = threading.RLock()
        self.timer = None
        self.ws_server = WebsocketServer(port, host)

        def send_to_client(client, server):
            with self.lock:
                server.send_message(client, self.frame)

        self.ws_server.set_fn_new_client(send_to_client)
        t = threading.Thread(target=self.ws_server.run_forever)
        t.daemon = True
        t.start()

    def build_graph(self, mon):
        nodes = []

        for cs in mon.cs.values():
            nodes.append({"id": cs.id,
                          "name": cs.name,
                          "load": (100*cs.active_jobs)/cs.maxjobs})

        links = []
        for job in mon.jobs.values():
            if job.host_id not in mon.cs or job.client_id not in mon.cs:
                continue
            c, s = mon.cs[job.client_id], mon.cs[job.host_id]

            # Don't double-add links.
            add = True
            for l in links:
                if l["source"] == c.id and l["target"] == s.id:
                    add = False

            if add:
                links.append({"source": c.id, "target": s.id, "value": 10})

        frame = {
            "timestamp": 0,
            "index": 0,
            "nodes": nodes,
            "links": links,
        }

        return json.dumps(frame)

    def publish(self, mon):
        with self.lock:
            self.frame = self.build_graph(mon)
            self.notify()

    def notify(self):
        now = time.time()
        with self.lock:
            if self.frame == self.last_sent_frame:
                # Frame hasn't changed, don't resend.
                return
            elif (now >= self.next_time_to_send and self.timer is None):
                # We can send.
                self.broadcast()
            elif self.timer is None:
                # We must reschedule.
                self.timer = threading.Timer(self.next_time_to_send - now,
                                             self.broadcast)
                self.timer.start()

    def broadcast(self):
        with self.lock:
            if self.timer is not None:
                self.timer.cancel()
            self.timer = None
            self.next_time_to_send = time.time() + self.MIN_SEND_GAP_S
            self.last_sent_frame = self.frame
            self.ws_server.send_message_to_all(self.frame)
