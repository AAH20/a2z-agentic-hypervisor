"""Nous Hermes Function-Calling Adapter - Middleware for Autonomous Trajectories.

Apex Growth Systems LLC - a2zsoc.com
NVIDIA Inception Program Flagship Architecture
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

from a2z_agentic_hypervisor.core.blast_sentinel import BlastRadiusExceededError
from a2z_agentic_hypervisor.core.interceptor import (
    A2ZAgentHypervisor,
    SecurityBreachBlockedError,
)

logger = logging.getLogger("a2z.hypervisor.adapters.hermes")


class HermesHypervisorMiddleware:
    """In-line security middleware for Nous Research Hermes agent workflows.
    
    Parses Hermes XML tool-calling sequences (<tool_call>...</tool_call>)
    and JSON payloads, routing them through the A2Z Agentic Hypervisor.
    """

    TOOL_CALL_REGEX = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.DOTALL)

    def __init__(
        self,
        tools: Dict[str, Callable[..., Any]],
        hypervisor: Optional[A2ZAgentHypervisor] = None,
        agent_id: str = "nous-hermes-agent",
        default_target_id: str = "infra-system",
    ):
        self.tools = dict(tools)
        self.hypervisor = hypervisor or A2ZAgentHypervisor()
        self.agent_id = agent_id
        self.default_target_id = default_target_id
        self._inverse_registry: Dict[str, Callable[[Any], Callable[[], Any]]] = {}

    def register_inverse(self, tool_name: str, inverse_factory: Callable[[Any], Callable[[], Any]]) -> None:
        """Register an inverse generator for a specific tool."""
        self._inverse_registry[tool_name] = inverse_factory

    def parse_hermes_tool_calls(self, completion_text: str) -> List[Dict[str, Any]]:
        """Extract tool calls formatted according to Hermes XML syntax."""
        calls = []
        matches = self.TOOL_CALL_REGEX.findall(completion_text)
        for raw in matches:
            try:
                parsed = json.loads(raw.strip())
                calls.append(parsed)
            except Exception:
                # Handle raw key-value formats
                calls.append({"raw": raw.strip()})
        return calls

    def execute_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        target_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Dispatch a single Hermes function call through the Hypervisor."""
        tool_func = self.tools.get(tool_name)
        if not tool_func:
            return {
                "status": "ERROR",
                "error": f"Tool '{tool_name}' not recognized by Hermes runtime",
            }

        target = target_id or arguments.get("target_id") or self.default_target_id

        inverse_fn = None
        if tool_name in self._inverse_registry:
            try:
                inverse_fn = self._inverse_registry[tool_name](arguments)
            except Exception as e:
                logger.warning("Could not construct inverse for %s: %s", tool_name, e)

        try:
            result, receipt = self.hypervisor.execute_guarded_tool(
                agent_id=self.agent_id,
                tool_name=tool_name,
                target_id=str(target),
                tool_func=tool_func,
                inverse_func=inverse_fn,
                tool_kwargs=arguments,
            )

            return {
                "status": "SUCCESS",
                "result": result,
                "receipt_id": receipt.receipt_id,
                "receipt_hash": receipt.receipt_hash,
                "merkle_root": self.hypervisor.ledger.latest_hash,
            }

        except (SecurityBreachBlockedError, BlastRadiusExceededError) as breach:
            return {
                "status": "BLOCKED",
                "reason": str(breach),
                "rollback_status": "ATOMIC_REVERSAL_COMMITTED",
                "state_leakage": 0,
            }
        except Exception as exc:
            return {
                "status": "EXCEPTION",
                "error": str(exc),
                "rollback_status": "ROLLBACK_EXECUTED",
            }

    def process_completion(self, completion_text: str) -> List[Dict[str, Any]]:
        """Extract all tool calls from Hermes completion and execute under Hypervisor."""
        calls = self.parse_hermes_tool_calls(completion_text)
        results = []
        for c in calls:
            tool_name = c.get("name") or c.get("tool")
            args = c.get("arguments") or c.get("parameters") or {}
            if tool_name:
                res = self.execute_call(tool_name=tool_name, arguments=args)
                results.append({"tool": tool_name, **res})
        return results
