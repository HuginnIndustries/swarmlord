"""Packet I/O — discovery, reading, atomic writing, log/index updates."""

from __future__ import annotations

from swarmlord.packets.discovery import (
    DiscoveredPacket,
    discover_packets,
    find_packet,
)
from swarmlord.packets.index import (
    IndexEntry,
    read_index,
    upsert_index_entry,
)
from swarmlord.packets.reader import (
    PacketBundle,
    load_packet,
    load_status,
    load_workflow,
)
from swarmlord.packets.thread_log import append_thread_log
from swarmlord.packets.writer import write_status, write_text_atomic

__all__ = [
    "DiscoveredPacket",
    "IndexEntry",
    "PacketBundle",
    "append_thread_log",
    "discover_packets",
    "find_packet",
    "load_packet",
    "load_status",
    "load_workflow",
    "read_index",
    "upsert_index_entry",
    "write_status",
    "write_text_atomic",
]
