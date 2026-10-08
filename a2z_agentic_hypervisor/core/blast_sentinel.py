"""Topological Blast-Radius Sentinel - Causal Reachability Engine.

Apex Growth Systems LLC - a2zsoc.com
NVIDIA Inception Program Flagship Architecture
Zero external dependencies (Python 3.10+ standard library).
"""

from __future__ import annotations

import collections
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


class BlastRadiusExceededError(Exception):
    """Raised when an agent tool action exceeds the allowable topological blast radius."""

    def __init__(self, target_id: str, blast_radius: float, max_blast_radius: float, details: Optional[Dict] = None):
        super().__init__(
            f"Action on target '{target_id}' blocked: blast radius {blast_radius:.3f} "
            f"exceeds ceiling {max_blast_radius:.3f}"
        )
        self.target_id = target_id
        self.blast_radius = blast_radius
        self.max_blast_radius = max_blast_radius
        self.details = details or {}


@dataclass
class InfraNode:
    """Represents an infrastructure component or dependency node."""

    node_id: str
    criticality_weight: float = 1.0  # Range: [0.0, 10.0]
    category: str = "service"
    metadata: Dict[str, str] = field(default_factory=dict)


class BlastSentinel:
    """Evaluates causal blast radius attenuation over an infrastructure dependency graph.
    
    Formula:
        B(v) = Sum_{u in Reach(v)} w(u) * (gamma ^ d(v, u))
    """

    def __init__(
        self,
        default_gamma: float = 0.85,
        default_max_blast: float = 25.0,
    ):
        self.gamma = default_gamma
        self.max_blast = default_max_blast
        self.nodes: Dict[str, InfraNode] = {}
        self.adjacency: Dict[str, List[Tuple[str, float]]] = collections.defaultdict(list)  # u -> list of (v, weight)

    def register_node(
        self,
        node_id: str,
        criticality_weight: float = 1.0,
        category: str = "service",
        metadata: Optional[Dict[str, str]] = None,
    ) -> InfraNode:
        """Register or update an infrastructure node."""
        node = InfraNode(
            node_id=node_id,
            criticality_weight=max(0.0, float(criticality_weight)),
            category=category,
            metadata=dict(metadata or {}),
        )
        self.nodes[node_id] = node
        return node

    def add_dependency(self, source_id: str, target_id: str, edge_weight: float = 1.0) -> None:
        """Register a directed dependency: source_id -> target_id (target depends on source)."""
        if source_id not in self.nodes:
            self.register_node(source_id)
        if target_id not in self.nodes:
            self.register_node(target_id)
        self.adjacency[source_id].append((target_id, edge_weight))

    def compute_blast_radius(self, target_id: str, gamma: Optional[float] = None) -> Tuple[float, Dict[str, float]]:
        """Compute the attenuated blast radius B(v) for an action targeting target_id.
        
        Returns:
            Tuple of (total_blast_score, dict_of_node_contributions)
        """
        if target_id not in self.nodes:
            # Unmapped node gets baseline target weight
            return 1.0, {target_id: 1.0}

        decay = self.gamma if gamma is None else gamma
        contributions: Dict[str, float] = {}
        
        # Breadth-first search for shortest topological path distances d(v, u)
        visited_distances: Dict[str, int] = {target_id: 0}
        queue = collections.deque([(target_id, 0)])

        while queue:
            curr_id, dist = queue.popleft()
            for neighbor_id, _ in self.adjacency.get(curr_id, []):
                if neighbor_id not in visited_distances:
                    visited_distances[neighbor_id] = dist + 1
                    queue.append((neighbor_id, dist + 1))

        # Attenuation calculation
        total_score = 0.0
        for node_id, dist in visited_distances.items():
            node = self.nodes.get(node_id)
            weight = node.criticality_weight if node else 1.0
            attenuated_weight = weight * (decay ** dist)
            contributions[node_id] = attenuated_weight
            total_score += attenuated_weight

        return total_score, contributions

    def check_and_enforce(
        self,
        target_id: str,
        custom_max_blast: Optional[float] = None,
        gamma: Optional[float] = None,
    ) -> float:
        """Calculate blast radius and enforce ceiling invariant B(v) <= B_max.
        
        Raises BlastRadiusExceededError if invariant is violated.
        Returns the computed blast score on success.
        """
        ceiling = self.max_blast if custom_max_blast is None else custom_max_blast
        score, contributions = self.compute_blast_radius(target_id, gamma=gamma)

        if score > ceiling:
            raise BlastRadiusExceededError(
                target_id=target_id,
                blast_radius=score,
                max_blast_radius=ceiling,
                details={"contributions": contributions, "node_count": len(contributions)},
            )

        return score
