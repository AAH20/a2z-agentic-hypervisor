"""In-Line Tool Interceptor & Proxy Engine - Real-Time Autonomous Hypervisor.

Apex Growth Systems LLC - a2zsoc.com
NVIDIA Inception Program Flagship Architecture
Zero external dependencies (Python 3.10+ standard library).
"""

from __future__ import annotations

import functools
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from a2z_agentic_hypervisor.core.action_ledger import ActionLedger, ActionReceipt
from a2z_agentic_hypervisor.core.blast_sentinel import BlastRadiusExceededError, BlastSentinel
from a2z_agentic_hypervisor.core.memory import EpisodicSOCMemory
from a2z_agentic_hypervisor.core.rollback import RollbackExecutionError, RollbackJournal

logger = logging.getLogger("a2z.hypervisor.interceptor")


class SecurityBreachBlockedError(Exception):
    """Raised when an in-line tool call violates security pre-conditions or guardrails."""

    def __init__(self, reason: str, tool_name: str, payload: Any, agent_id: str):
        super().__init__(f"Security breach blocked on tool '{tool_name}' by agent '{agent_id}': {reason}")
        self.reason = reason
        self.tool_name = tool_name
        self.payload = payload
        self.agent_id = agent_id


# Destructive shell / database / cloud API command patterns
DANGEROUS_PATTERNS = [
    re.compile(r"\brm\s+-[rRfF]{1,3}\s+[/~*]", re.IGNORECASE),
    re.compile(r"\b(drop|truncate|alter)\s+(database|table|schema|role)\b", re.IGNORECASE),
    re.compile(r"\b(format|mkfs|fdisk|dd\s+if=/dev/zero)\b", re.IGNORECASE),
    re.compile(r"\b(shutdown|reboot|init\s+0|halt)\b", re.IGNORECASE),
    re.compile(r"\b(iptables\s+-F|ufw\s+disable)\b", re.IGNORECASE),
    re.compile(r"\bkubectl\s+delete\s+(all|namespace|nodes?)\b", re.IGNORECASE),
    re.compile(r"\b(cat\s+/etc/shadow|sudo\s+su|chmod\s+-R\s+777(\s+[/~*])?|chmod\s+777)", re.IGNORECASE),
    re.compile(r"(ignore|disregard)\s+(all\s+|prior\s+|previous\s+)?(instructions?|rules?|guidelines?|policies|prompts?|guardrails?)", re.IGNORECASE),
    re.compile(r"(system\s+override|new\s+system\s+instruction|system\s+prompt\s+override)", re.IGNORECASE),
    re.compile(r"\b(dump|exfiltrate)\s+(all\s+)?(secret|credentials?|passwords?|tokens?)\b", re.IGNORECASE),
]


class A2ZAgentHypervisor:
    """The central Cyber Defense Hypervisor and Compensatory Rollback Engine.
    
    Protects infrastructure against autonomous agent drift, hallucinated destructive mutations,
    and indirect prompt injections.
    """

    def __init__(
        self,
        tenant_id: str = "apex-sovereign-soc",
        default_gamma: float = 0.85,
        default_max_blast: float = 25.0,
        enable_strict_preconditions: bool = True,
        nim_guard_client: Optional[Any] = None,
    ):
        self.tenant_id = tenant_id
        self.enable_strict_preconditions = enable_strict_preconditions
        self.nim_guard_client = nim_guard_client

        # Core subsystems (Pure Python Stdlib)
        self.ledger = ActionLedger(tenant_id=tenant_id)
        self.sentinel = BlastSentinel(default_gamma=default_gamma, default_max_blast=default_max_blast)
        self.journal = RollbackJournal()
        self.memory = EpisodicSOCMemory()

        self._blocked_attacks: int = 0
        self._successful_actions: int = 0

    @property
    def metrics(self) -> Dict[str, Any]:
        """Telemetry metrics for SOC dashboards."""
        return {
            "tenant_id": self.tenant_id,
            "total_receipts": self.ledger.total_receipts,
            "active_journal_entries": self.journal.entry_count,
            "blocked_attacks": self._blocked_attacks,
            "successful_actions": self._successful_actions,
            "indexed_incidents": len(self.memory.incidents),
            "latest_merkle_root": self.ledger.compute_merkle_root(),
        }

    def audit_preconditions(self, agent_id: str, tool_name: str, target_id: str, payload: Any) -> None:
        """Validate safety pre-conditions and semantic integrity before dispatch."""
        if not self.enable_strict_preconditions:
            return

        payload_str = str(payload)

        # 1. Regex dangerous command detection
        for pat in DANGEROUS_PATTERNS:
            if pat.search(payload_str):
                raise SecurityBreachBlockedError(
                    reason=f"Dangerous command pattern detected: {pat.pattern}",
                    tool_name=tool_name,
                    payload=payload,
                    agent_id=agent_id,
                )

        # 2. Memory threat pattern check
        if self.memory.has_known_threat_pattern(f"{tool_name} {target_id} {payload_str}", threshold=0.75):
            raise SecurityBreachBlockedError(
                reason="Semantic similarity to previously blocked attack in SOC memory",
                tool_name=tool_name,
                payload=payload,
                agent_id=agent_id,
            )

        # 3. Optional NIM / NeMo guardrail client
        if self.nim_guard_client is not None:
            try:
                verdict = self.nim_guard_client.inspect(tool_name=tool_name, payload=payload)
                if not verdict.get("allowed", True):
                    raise SecurityBreachBlockedError(
                        reason=f"NVIDIA NIM Guardrail Tripwire: {verdict.get('reason', 'Policy violation')}",
                        tool_name=tool_name,
                        payload=payload,
                        agent_id=agent_id,
                    )
            except SecurityBreachBlockedError:
                raise
            except Exception as e:
                logger.warning("NIM guardrail check failed open/closed: %s", e)

    def execute_guarded_tool(
        self,
        agent_id: str,
        tool_name: str,
        target_id: str,
        tool_func: Callable[..., Any],
        inverse_func: Optional[Callable[[], Any]] = None,
        tool_args: Optional[Tuple] = None,
        tool_kwargs: Optional[Dict[str, Any]] = None,
        custom_max_blast: Optional[float] = None,
        inverse_desc: str = "",
    ) -> Tuple[Any, ActionReceipt]:
        """Synchronously intercept, validate, execute, journal, and emit receipt for a tool call."""
        args = tool_args or ()
        kwargs = tool_kwargs or {}
        payload = {"args": args, "kwargs": kwargs}

        try:
            # Step 1: Pre-condition and security audit
            self.audit_preconditions(agent_id, tool_name, target_id, payload)

            # Step 2: Blast-radius topological reachability check
            self.sentinel.check_and_enforce(target_id, custom_max_blast=custom_max_blast)

            # Step 3: Register inverse in RollbackJournal before mutating
            if inverse_func is not None:
                self.journal.record(
                    agent_id=agent_id,
                    tool_name=tool_name,
                    target_id=target_id,
                    forward_payload=payload,
                    inverse_action=inverse_func,
                    inverse_description=inverse_desc or f"Undo {tool_name} on {target_id}",
                )

            # Step 4: Dispatch execution
            result = tool_func(*args, **kwargs)

            # Step 5: Cryptographic receipt emission (fde-bounty-snr standard)
            receipt = self.ledger.record_action(
                agent_id=agent_id,
                tool_name=tool_name,
                target_id=target_id,
                payload=payload,
                metadata={"status": "COMMITTED"},
            )

            self._successful_actions += 1
            return result, receipt

        except (SecurityBreachBlockedError, BlastRadiusExceededError) as breach_err:
            self._blocked_attacks += 1
            logger.error("A2Z Hypervisor blocked attack: %s", breach_err)

            # Index into Episodic SOC Memory
            attack_type = "BLAST_RADIUS_OVERRUN" if isinstance(breach_err, BlastRadiusExceededError) else "SECURITY_BREACH"
            self.memory.record_incident(
                agent_id=agent_id,
                attack_vector=attack_type,
                target_id=target_id,
                tool_name=tool_name,
                payload_repr=str(payload),
                reason=str(breach_err),
            )

            # LIFO Rollback
            rollback_summary = self.journal.rollback_all()
            logger.info("Executed compensatory rollback: %s", rollback_summary)
            raise breach_err

        except Exception as exc:
            # Operational execution failure - trigger compensatory rollback
            logger.error("Execution error during %s: %s; rolling back transaction stack", tool_name, exc)
            self.journal.rollback_all()
            raise exc

    def guard_tool(
        self,
        agent_id: str,
        target_id: str,
        inverse_factory: Optional[Callable[..., Callable[[], Any]]] = None,
    ):
        """Decorator to wrap any standalone Python function with the Hypervisor."""
        def decorator(func: Callable):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                tool_name = func.__name__
                inverse_fn = inverse_factory(*args, **kwargs) if inverse_factory else None
                res, _ = self.execute_guarded_tool(
                    agent_id=agent_id,
                    tool_name=tool_name,
                    target_id=target_id,
                    tool_func=func,
                    inverse_func=inverse_fn,
                    tool_args=args,
                    tool_kwargs=kwargs,
                )
                return res
            return wrapper
        return decorator
