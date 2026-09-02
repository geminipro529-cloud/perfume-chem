# Complex Perfumery Bridge Lane

This directory is an evidence-transport boundary, not canonical scientific or formula authority.

`PROTOCOL.md` is intentionally not supplied by the MCP bridge change. The exact Chat Bridge Protocol v2.1 bytes must be obtained from the authoritative local source, stored at `chat_bridge/complex_perfumery/PROTOCOL.md`, and pinned through `PERFUME_CHEM_PROTOCOL_SHA256`. The bridge refuses packet staging when that file or hash is absent, mismatched, non-UTF-8, or lacks the protocol identity marker.

Packets are created only beneath:

```text
inbox/<conversation-id>/<nonce>/PACKET.json
```

The inbox is ignored by Git so raw packet material is not committed accidentally. Packet creation does not imply acknowledgement, installation, claim acceptance, formula mutation, or canonical promotion.
