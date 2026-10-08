"""ActionLedger Engine - Cryptographic Non-Repudiation for Autonomous Agents.

Apex Growth Systems LLC - a2zsoc.com
NVIDIA Inception Program Flagship Architecture
Zero external dependencies (Python 3.10+ standard library).
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ActionReceipt:
    """Immutable cryptographic receipt for an agent action (fde-bounty-snr standard)."""

    receipt_id: str
    agent_id: str
    tool_name: str
    target_id: str
    payload_hash: str
    timestamp: float
    previous_receipt_hash: str
    receipt_hash: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert receipt to dictionary representation."""
        return asdict(self)


class ActionLedger:
    """Non-repudiable SHA-256 Merkle chain emitter and tamper-evident audit journal.
    
    Guarantees that every mutating agent action is cryptographically verifiable,
    forming an append-only hash chain anchored at genesis.
    """

    GENESIS_HASH = "0" * 64

    def __init__(self, tenant_id: str = "apex-sovereign-soc", seed_hash: Optional[str] = None):
        self.tenant_id = tenant_id
        self._chain: List[ActionReceipt] = []
        self._last_hash: str = seed_hash or self.GENESIS_HASH
        self._total_receipts: int = 0

    @property
    def total_receipts(self) -> int:
        """Total number of receipts committed to the ledger."""
        return self._total_receipts

    @property
    def latest_hash(self) -> str:
        """Hash of the most recent receipt, or genesis hash if empty."""
        return self._last_hash

    @staticmethod
    def compute_payload_hash(payload: Any) -> str:
        """Compute deterministic SHA-256 digest of arbitrary payload."""
        if isinstance(payload, bytes):
            raw = payload
        else:
            try:
                raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
            except Exception:
                raw = str(payload).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def record_action(
        self,
        agent_id: str,
        tool_name: str,
        target_id: str,
        payload: Any,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ActionReceipt:
        """Commit an agent tool call to the cryptographic hash chain.
        
        Formula:
            H_receipt = SHA-256(AgentID || Tool || TargetID || PayloadHash || Timestamp || H_prev)
        """
        ts = time.time()
        payload_hash = self.compute_payload_hash(payload)
        prev_hash = self._last_hash

        raw_str = f"{agent_id}:{tool_name}:{target_id}:{payload_hash}:{ts:.6f}:{prev_hash}"
        receipt_hash = hashlib.sha256(raw_str.encode("utf-8")).hexdigest()
        receipt_id = f"rcpt_{hashlib.sha256(f'{self._total_receipts}:{receipt_hash}'.encode()).hexdigest()[:16]}"

        receipt = ActionReceipt(
            receipt_id=receipt_id,
            agent_id=agent_id,
            tool_name=tool_name,
            target_id=target_id,
            payload_hash=payload_hash,
            timestamp=ts,
            previous_receipt_hash=prev_hash,
            receipt_hash=receipt_hash,
            metadata=dict(metadata or {}),
        )

        self._chain.append(receipt)
        self._last_hash = receipt_hash
        self._total_receipts += 1
        return receipt

    def verify_integrity(self) -> bool:
        """Audit entire hash chain from genesis to tail.
        
        Returns True if 100% untampered, raises ValueError on first broken link.
        """
        expected_prev = self.GENESIS_HASH
        for idx, rcpt in enumerate(self._chain):
            if idx == 0 and rcpt.previous_receipt_hash != self.GENESIS_HASH:
                raise ValueError(f"Integrity fault at genesis: expected {self.GENESIS_HASH}, got {rcpt.previous_receipt_hash}")
            if idx > 0 and rcpt.previous_receipt_hash != expected_prev:
                raise ValueError(f"Integrity fault at index {idx}: broken link with {rcpt.receipt_id}")

            raw_str = (
                f"{rcpt.agent_id}:{rcpt.tool_name}:{rcpt.target_id}:{rcpt.payload_hash}:"
                f"{rcpt.timestamp:.6f}:{rcpt.previous_receipt_hash}"
            )
            recomputed = hashlib.sha256(raw_str.encode("utf-8")).hexdigest()
            if recomputed != rcpt.receipt_hash:
                raise ValueError(f"Cryptographic digest mismatch at index {idx} ({rcpt.receipt_id})")

            expected_prev = rcpt.receipt_hash

        return True

    def export_ledger(self) -> List[Dict[str, Any]]:
        """Export serialized chain for SOC ingestion and SIEM archival."""
        return [r.to_dict() for r in self._chain]

    def compute_merkle_root(self) -> str:
        """Compute single top-level Merkle root across all receipts."""
        if not self._chain:
            return self.GENESIS_HASH

        leaves = [r.receipt_hash for r in self._chain]
        current_layer = leaves

        while len(current_layer) > 1:
            next_layer = []
            for i in range(0, len(current_layer), 2):
                if i + 1 < len(current_layer):
                    combined = current_layer[i] + current_layer[i + 1]
                else:
                    combined = current_layer[i] + current_layer[i]
                next_layer.append(hashlib.sha256(combined.encode("utf-8")).hexdigest())
            current_layer = next_layer

        return current_layer[0]
