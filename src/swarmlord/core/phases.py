"""Phase enum.

Phases describe what work is happening *inside* a stage. ``MEMORY`` is
transient and can be re-entered from any stage to refresh the packet's
graphify output.
"""

from __future__ import annotations

from enum import StrEnum


class Phase(StrEnum):
    IDEA = "idea"
    DISCOVERY = "discovery"
    BUILD_SPEC = "build_spec"
    EXTRACTION = "extraction"
    MEMORY = "memory"
