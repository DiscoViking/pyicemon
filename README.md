# pyicemon
Web front-end and framework for monitoring an icecream distributed build cluster.


## Status

**Icemon API:** All messages implemented as protocol version 22.  Protocol version negotiation not supported.

**Generic monitor:** Fully implemented with generic publisher infrastructure.

**Websocket Publisher:** Implemented to send a json representation of the cluster down any connected websockets.

**Web front-end:** Not currently hosted by the monitor/publisher itself.  But otherwise fundamentally works.  Displays the cluster activity using d3.js force graph.


## Class Design

**Message (and subclasses):** Represent a single message from the scheduler.  They each know how to decode themselves from wire-data.

**Connection:** Handles a persistent connection to a scheduler.  Reads messages off the wire and returns them as parsed Message types.

**Monitor:** Maintains a view of the current state of the cluster by reading messages from a Connection and updating itself accordingly.  Reports changes in cluster state to a Publisher.

**Publisher:** Publishes information about the cluster to an outside source.


## TODO

  - Implement protocol negotiation and interoperability between different protocol versions.
  - Generally improve quality of web view.
