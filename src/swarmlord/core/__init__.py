"""Core domain: schemas, enums, gates, errors. No I/O dependencies."""

from __future__ import annotations

from swarmlord.core.errors import (
    GateFailure,
    IllegalTransition,
    PacketSchemaError,
    SwarmLordError,
    TemplateRenderError,
    WorkflowParseError,
)
from swarmlord.core.gates import GateResult, evaluate_gate, evaluate_predicate
from swarmlord.core.models import (
    AgentConfig,
    GateConfig,
    MemoryStatus,
    PacketStatus,
    Predicate,
    RunRecord,
    WorkflowDefinition,
    WorkflowHooks,
)
from swarmlord.core.phases import Phase
from swarmlord.core.stages import LEGAL_TRANSITIONS, Stage, can_transition

__all__ = [
    "LEGAL_TRANSITIONS",
    "AgentConfig",
    "GateConfig",
    "GateFailure",
    "GateResult",
    "IllegalTransition",
    "MemoryStatus",
    "PacketSchemaError",
    "PacketStatus",
    "Phase",
    "Predicate",
    "RunRecord",
    "Stage",
    "SwarmLordError",
    "TemplateRenderError",
    "WorkflowDefinition",
    "WorkflowHooks",
    "WorkflowParseError",
    "can_transition",
    "evaluate_gate",
    "evaluate_predicate",
]
