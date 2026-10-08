"""A2Z Agentic Hypervisor - Autonomous Agent Cyber Defense & Atomic Rollback Engine.

Apex Growth Systems LLC - a2zsoc.com
NVIDIA Inception Program Flagship Architecture
"""

from a2z_agentic_hypervisor.adapters.hermes import HermesHypervisorMiddleware
from a2z_agentic_hypervisor.adapters.langchain import GuardedToolNode
from a2z_agentic_hypervisor.core.action_ledger import ActionLedger, ActionReceipt
from a2z_agentic_hypervisor.core.blast_sentinel import (
    BlastRadiusExceededError,
    BlastSentinel,
    InfraNode,
)
from a2z_agentic_hypervisor.core.interceptor import (
    A2ZAgentHypervisor,
    SecurityBreachBlockedError,
)
from a2z_agentic_hypervisor.core.memory import EpisodicSOCMemory, IncidentRecord
from a2z_agentic_hypervisor.core.rollback import (
    JournalEntry,
    RollbackExecutionError,
    RollbackJournal,
)
from a2z_agentic_hypervisor.nvidia.morpheus_emitter import MorpheusTelemetryEmitter
from a2z_agentic_hypervisor.nvidia.nemo_rails import NeMoGuardrailsAdapter
from a2z_agentic_hypervisor.nvidia.nim_client import NIMClient
from a2z_agentic_hypervisor.redteam.bench_redteam import (
    RedTeamRunner,
    generate_benchmark_vectors,
)

__version__ = "1.1.0"
__author__ = "Apex Growth Systems LLC <aah@a2zsoc.com>"
__homepage__ = "https://a2zsoc.com"

__all__ = [
    "A2ZAgentHypervisor",
    "ActionLedger",
    "ActionReceipt",
    "BlastSentinel",
    "BlastRadiusExceededError",
    "InfraNode",
    "RollbackJournal",
    "RollbackExecutionError",
    "JournalEntry",
    "EpisodicSOCMemory",
    "IncidentRecord",
    "SecurityBreachBlockedError",
    "NIMClient",
    "NeMoGuardrailsAdapter",
    "MorpheusTelemetryEmitter",
    "RedTeamRunner",
    "generate_benchmark_vectors",
    "GuardedToolNode",
    "HermesHypervisorMiddleware",
    "__version__",
]
