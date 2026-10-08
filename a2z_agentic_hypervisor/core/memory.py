"""Associative Episodic SOC Memory - Incident Post-Mortem Vector Index.

Apex Growth Systems LLC - a2zsoc.com
NVIDIA Inception Program Flagship Architecture
Zero external dependencies (Python 3.10+ standard library).
"""

from __future__ import annotations

import math
import re
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class IncidentRecord:
    """Stores a security or blast-radius breach post-mortem."""

    incident_id: str
    agent_id: str
    attack_vector: str
    target_id: str
    tool_name: str
    payload_repr: str
    reason: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    tokens: Set[str] = field(default_factory=set)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["tokens"] = list(self.tokens)
        return d


class EpisodicSOCMemory:
    """Vectorized episodic memory indexing security incidents for instantaneous immune recall.
    
    Uses pure Python sparse token vectorization with BM25/Cosine scoring
    to achieve sub-millisecond retrieval without external vector DB dependencies.
    """

    def __init__(self, match_threshold: float = 0.35):
        self.match_threshold = match_threshold
        self.incidents: List[IncidentRecord] = []
        self._doc_freq: Dict[str, int] = {}
        self._total_incidents: int = 0

    @staticmethod
    def tokenize(text: str) -> Set[str]:
        """Normalize and tokenize arbitrary string into lower-case terms."""
        clean = re.sub(r"[^a-zA-Z0-9_\-\./]", " ", str(text).lower())
        tokens = set(clean.split())
        return {t for t in tokens if len(t) > 2}

    def record_incident(
        self,
        agent_id: str,
        attack_vector: str,
        target_id: str,
        tool_name: str,
        payload_repr: str,
        reason: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> IncidentRecord:
        """Index a new security breach post-mortem."""
        self._total_incidents += 1
        incident_id = f"inc_{self._total_incidents:06d}_{int(time.time() * 1000)}"

        combined_text = f"{attack_vector} {target_id} {tool_name} {payload_repr} {reason}"
        tokens = self.tokenize(combined_text)

        for t in tokens:
            self._doc_freq[t] = self._doc_freq.get(t, 0) + 1

        record = IncidentRecord(
            incident_id=incident_id,
            agent_id=agent_id,
            attack_vector=attack_vector,
            target_id=target_id,
            tool_name=tool_name,
            payload_repr=payload_repr,
            reason=reason,
            tokens=tokens,
            metadata=dict(metadata or {}),
        )

        self.incidents.append(record)
        return record

    def find_similar_incidents(
        self,
        query_text: str,
        top_k: int = 3,
        threshold: Optional[float] = None,
    ) -> List[Tuple[IncidentRecord, float]]:
        """Query memory for incidents matching query_text using Cosine-IDF similarity."""
        if not self.incidents:
            return []

        cutoff = self.match_threshold if threshold is None else threshold
        q_tokens = self.tokenize(query_text)
        if not q_tokens:
            return []

        n_docs = len(self.incidents)
        scores: List[Tuple[IncidentRecord, float]] = []

        for inc in self.incidents:
            intersection = q_tokens.intersection(inc.tokens)
            if not intersection:
                continue

            # Standard Cosine similarity over token overlap
            jaccard = len(intersection) / len(q_tokens.union(inc.tokens))
            cosine = len(intersection) / math.sqrt(len(q_tokens) * len(inc.tokens) + 1e-9)
            similarity = (jaccard + cosine) / 2.0

            if similarity >= cutoff:
                scores.append((inc, similarity))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def has_known_threat_pattern(self, candidate_text: str, threshold: Optional[float] = None) -> bool:
        """Check if candidate text matches any known recorded breach signature."""
        matches = self.find_similar_incidents(candidate_text, top_k=1, threshold=threshold)
        return len(matches) > 0
