# pyicemon
Web front-end and framework for monitoring an icecream distributed build cluster.


## Usage

Basic usage:

    python monitor.py <scheduler_hostname> <scheduler_port>

Then open visage.html in your browser.


## Status

**Icemon API:** All messages implemented as protocol version 22.  Protocol version negotiation not supported.

**Generic monitor:** Fully implemented with generic publisher infrastructure.

**Websocket Publisher:** Implemented to send a json representation of the cluster down any connected websockets.

**Web front-end:** Not currently hosted by the monitor/publisher itself.  But otherwise fundamentally works.  Displays the cluster activity using d3.js force graph.


## Class Design

**Message (and subclasses):** Represent a single message from the scheduler.  They each know how to decode themselves from wire-data.

Usage:

```python
from pyicemon import messages

# Unpack a message from a byte string. (string must contain only exactly one message)
m = messages.unpack(wire_data)

# Pack message to a byte string.
data = m.pack()
```

**Connection:** Handles a persistent connection to a scheduler.  Reads messages off the wire and returns them as parsed Message types.

Usage:

```python
import pyicemon
from pyicemon import messages

scheduler_host, scheduler_port = "scheduler.com", 9999

# Open a connection to a server. (Also handles version negotiation)
conn = pyicemon.Connection(scheduler_host, scheduler_port)

# Send a message.
m = messages.LoginMessage()
conn.send_message(m)

# Receive messages.
while True:
    m = conn.get_message()
    print m
```

**Monitor:** Maintains a view of the current state of the cluster by reading messages from a Connection and updating itself accordingly.  Reports changes in cluster state to a Publisher.

Usage:

```python
import pyicemon

scheduler_host, scheduler_port = "scheduler.com", 9999
mon = pyicemon.Monitor(scheduler_host, scheduler_port)
mon.run() # Blocks forever.
```

**Publisher:** Publishes information about the cluster to an outside source.


## TODO

  - Implement protocol negotiation and interoperability between different protocol versions.
  - Generally improve quality of web view.
