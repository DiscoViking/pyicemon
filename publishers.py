import json
import time
import threading
from websocket_server import WebsocketServer


class WebsocketPublisher(object):
    """
    Publish cluster state as JSON over a websocket.

    Only sends CS state, and information on who is building on who.
    This is enough information to draw a graph of the cluster.
    Explicitly, does not send information on individual jobs.
    """

    MIN_SEND_GAP_S = 0.1
    """Minimum gap in seconds between sending messages to connected clients."""

    def __init__(self, host="0.0.0.0", port=9999):
        self.frame = ""
        self.nodes = ""
        self.links = ""
        self.last_sent_frame = ""
        self.last_sent_nodes = ""
        self.last_sent_links = ""
        self.next_time_to_send = 0
        self.lock = threading.RLock()
        self.timer = None
        self.ws_server = WebsocketServer(port, host)

        def send_to_client(client, server):
            with self.lock:
                server.send_message(client, self.build_graph(True))

        self.ws_server.set_fn_new_client(send_to_client)
        t = threading.Thread(target=self.ws_server.run_forever)
        t.daemon = True
        t.start()

    def build_nodes(self, mon):
        """Builds a JSON representation of the CS nodes in the cluster."""
        nodes = []

        for cs in mon.cs.values():
            nodes.append({"id": cs.id,
                          "name": cs.name,
                          "ip": cs.ip,
                          "load": (100*len(cs.active_jobs))/cs.maxjobs})

        return json.dumps(nodes)

    def build_links(self, mon):
        """
        Builds a JSON representation of the links in the cluster.

        There is one link A->B if A has one or more jobs building on B.
        """
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

        return json.dumps(links)

    def build_graph(self, full=False):
        """Builds a full JSON representation of a graph of the cluster."""
        frame = '{"timestamp": 0, "index": 0'

        if full or self.nodes != self.last_sent_nodes:
            frame += ', "nodes": ' + self.nodes

        if full or self.links != self.last_sent_links:
            frame += ', "links": ' + self.links

        frame += '}'

        return frame

    def publish(self, mon):
        """
        Called by the Monitor to indicate new cluster state.

        Update our internal state, and notify clients if appropriate.
        """
        with self.lock:
            self.nodes = self.build_nodes(mon)
            self.links = self.build_links(mon)
            self.frame = self.build_graph()
            self.notify()

    def notify(self):
        """Send updates to clients if necessary."""
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
        """Actually broadcast cluster state to all connected clients."""
        with self.lock:
            if self.timer is not None:
                self.timer.cancel()
            self.timer = None
            self.next_time_to_send = time.time() + self.MIN_SEND_GAP_S
            self.last_sent_frame = self.frame
            self.last_sent_nodes = self.nodes
            self.last_sent_links = self.links
            self.ws_server.send_message_to_all(self.frame)
