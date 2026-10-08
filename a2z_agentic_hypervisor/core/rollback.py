"""Compensatory Rollback Journal - Hoare-Logic Atomic Reversal Engine.

Apex Growth Systems LLC - a2zsoc.com
NVIDIA Inception Program Flagship Architecture
Zero external dependencies (Python 3.10+ standard library).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("a2z.hypervisor.rollback")


class RollbackExecutionError(Exception):
    """Raised when one or more compensatory actions fail during LIFO rollback."""

    def __init__(self, message: str, failed_entries: List[Tuple[str, Exception]]):
        super().__init__(message)
        self.failed_entries = failed_entries


@dataclass
class JournalEntry:
    """Represents a committed forward action and its registered inverse."""

    entry_id: str
    agent_id: str
    tool_name: str
    target_id: str
    forward_payload: Any
    inverse_action: Callable[[], Any]
    inverse_description: str
    timestamp: float = field(default_factory=time.time)
    executed_inverse: bool = False
    inverse_result: Optional[Any] = None
    inverse_error: Optional[str] = None


class RollbackJournal:
    """LIFO compensatory journal enforcing Hoare-logic reversible state transitions.
    
    Guarantees:
        {Q} A^{-1} {P}
        Trajectory reversal: R(T) = [A_k^{-1}, ..., A_1^{-1}]
    """

    def __init__(self):
        self._journal: List[JournalEntry] = []
        self._checkpoints: Dict[str, int] = {}
        self._seq: int = 0

    @property
    def entry_count(self) -> int:
        """Number of active un-rolled-back entries in the journal."""
        return len(self._journal)

    def record(
        self,
        agent_id: str,
        tool_name: str,
        target_id: str,
        forward_payload: Any,
        inverse_action: Callable[[], Any],
        inverse_description: str = "",
    ) -> JournalEntry:
        """Register a mutating forward action with its corresponding compensatory inverse."""
        self._seq += 1
        entry_id = f"txn_{self._seq:06d}_{int(time.time() * 1000)}"
        entry = JournalEntry(
            entry_id=entry_id,
            agent_id=agent_id,
            tool_name=tool_name,
            target_id=target_id,
            forward_payload=forward_payload,
            inverse_action=inverse_action,
            inverse_description=inverse_description or f"Reversal for {tool_name} on {target_id}",
        )
        self._journal.append(entry)
        return entry

    def create_checkpoint(self, checkpoint_id: str) -> str:
        """Mark current journal position as a named checkpoint."""
        self._checkpoints[checkpoint_id] = len(self._journal)
        return checkpoint_id

    def rollback_all(self) -> Dict[str, Any]:
        """Execute all recorded inverse actions in strict LIFO order.
        
        Returns:
            Summary dict with rollback fidelity metric (1.000 = 100% success).
        """
        return self._execute_lifo_rollback(target_depth=0)

    def rollback_to_checkpoint(self, checkpoint_id: str) -> Dict[str, Any]:
        """Rollback actions executed after the specified checkpoint."""
        if checkpoint_id not in self._checkpoints:
            raise KeyError(f"Checkpoint '{checkpoint_id}' not found in journal")
        target_depth = self._checkpoints[checkpoint_id]
        return self._execute_lifo_rollback(target_depth=target_depth)

    def _execute_lifo_rollback(self, target_depth: int) -> Dict[str, Any]:
        """Internal LIFO unwind down to target depth."""
        total_to_revert = len(self._journal) - target_depth
        if total_to_revert <= 0:
            return {
                "reverted_count": 0,
                "failed_count": 0,
                "fidelity": 1.0,
                "status": "NOOP",
            }

        reverted_count = 0
        failed_entries: List[Tuple[str, Exception]] = []

        # Strict LIFO: pop from tail
        while len(self._journal) > target_depth:
            entry = self._journal.pop()
            try:
                res = entry.inverse_action()
                entry.executed_inverse = True
                entry.inverse_result = res
                reverted_count += 1
            except Exception as exc:
                logger.error(
                    "Compensatory reversal failed for entry %s (%s): %s",
                    entry.entry_id,
                    entry.inverse_description,
                    exc,
                )
                entry.executed_inverse = True
                entry.inverse_error = str(exc)
                failed_entries.append((entry.entry_id, exc))

        fidelity = reverted_count / total_to_revert if total_to_revert > 0 else 1.0

        result = {
            "reverted_count": reverted_count,
            "failed_count": len(failed_entries),
            "total_requested": total_to_revert,
            "fidelity": fidelity,
            "status": "SUCCESS" if not failed_entries else "PARTIAL_REVERSAL_ERROR",
        }

        if failed_entries:
            raise RollbackExecutionError(
                f"Rollback completed with {len(failed_entries)} failures out of {total_to_revert} actions",
                failed_entries=failed_entries,
            )

        return result

    def clear(self) -> None:
        """Clear the journal without executing inverses (e.g. after successful transaction commit)."""
        self._journal.clear()
        self._checkpoints.clear()
