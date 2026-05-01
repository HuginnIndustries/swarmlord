"""Walk a repo for project packets.

A *packet* is any directory that contains ``workflow/status.yaml``. The
discovery walker scopes itself to a ``projects/`` subdirectory by default but
will accept any root.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from swarmlord.core.errors import PacketSchemaError
from swarmlord.core.models import PacketStatus
from swarmlord.packets.reader import load_status


@dataclass(slots=True, frozen=True)
class DiscoveredPacket:
    """A packet on disk with its parsed status and root path."""

    root: Path
    status: PacketStatus

    @property
    def slug(self) -> str:
        return self.status.slug


def discover_packets(
    repo_root: Path,
    *,
    projects_subdir: str = "projects",
) -> list[DiscoveredPacket]:
    """Return every packet found under ``repo_root/projects_subdir``.

    Packets that fail schema validation are skipped silently here — callers
    that want a strict pass should use ``swarmlord validate --all``.
    """
    base = repo_root / projects_subdir
    if not base.is_dir():
        return []
    found: list[DiscoveredPacket] = []
    for status_file in sorted(base.glob("*/workflow/status.yaml")):
        packet_root = status_file.parent.parent
        try:
            status = load_status(packet_root)
        except (PacketSchemaError, FileNotFoundError):
            continue
        found.append(DiscoveredPacket(root=packet_root, status=status))
    return found


def find_packet(
    repo_root: Path,
    slug: str,
    *,
    projects_subdir: str = "projects",
) -> DiscoveredPacket | None:
    """Find a packet by slug. Matches against ``status.slug`` first, then folder name."""
    for packet in discover_packets(repo_root, projects_subdir=projects_subdir):
        if packet.status.slug == slug or packet.root.name == slug:
            return packet
    return None


def discover_failures(
    repo_root: Path,
    *,
    projects_subdir: str = "projects",
) -> list[tuple[Path, str]]:
    """Return ``(packet_root, error_message)`` for every packet that exists
    on disk but failed schema validation. Useful for surfacing broken
    packets in ``swarmlord list`` so they are not invisible to the user.
    """
    base = repo_root / projects_subdir
    if not base.is_dir():
        return []
    failures: list[tuple[Path, str]] = []
    for status_file in sorted(base.glob("*/workflow/status.yaml")):
        packet_root = status_file.parent.parent
        try:
            load_status(packet_root)
        except (PacketSchemaError, FileNotFoundError) as exc:
            failures.append((packet_root, str(exc).splitlines()[0]))
    return failures
