"""LangChain & LangGraph Adapter - GuardedToolNode with Atomic Rollback.

Apex Growth Systems LLC - a2zsoc.com
NVIDIA Inception Program Flagship Architecture
Zero hard dependencies on langchain; duck-types message interfaces.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Union

from a2z_agentic_hypervisor.core.blast_sentinel import BlastRadiusExceededError
from a2z_agentic_hypervisor.core.interceptor import (
    A2ZAgentHypervisor,
    SecurityBreachBlockedError,
)

logger = logging.getLogger("a2z.hypervisor.adapters.langchain")


class GuardedToolNode:
    """Drop-in transactional wrapper for LangGraph ToolNode or LangChain tool callers.
    
    Guarantees that every mutating agent tool invocation is intercepted,
    bounded by topological blast radius, logged in the SHA-256 ActionLedger,
    and rolled back atomically upon invariant tripwire breach.
    """

    def __init__(
        self,
        tools: Union[List[Any], Dict[str, Any]],
        hypervisor: Optional[A2ZAgentHypervisor] = None,
        inverse_registry: Optional[Dict[str, Callable[[Any], Callable[[], Any]]]] = None,
        agent_id: str = "langgraph-agent",
        default_target_id: str = "infra-runtime",
    ):
        self.hypervisor = hypervisor or A2ZAgentHypervisor()
        self.agent_id = agent_id
        self.default_target_id = default_target_id
        self.inverse_registry = inverse_registry or {}

        # Normalize tools dictionary: tool_name -> callable
        self.tools_by_name: Dict[str, Any] = {}
        if isinstance(tools, dict):
            self.tools_by_name = dict(tools)
        elif isinstance(tools, list):
            for t in tools:
                name = getattr(t, "name", getattr(t, "__name__", str(t)))
                self.tools_by_name[name] = t

    def register_inverse(self, tool_name: str, inverse_factory: Callable[[Any], Callable[[], Any]]) -> None:
        """Register an inverse generator for a specific tool.
        
        The inverse_factory receives the tool's arguments and returns a callable
        that undoes the tool's side effects.
        """
        self.inverse_registry[tool_name] = inverse_factory

    def invoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """LangGraph-compatible execution hook for state graph nodes."""
        messages = state.get("messages", [])
        if not messages:
            return {"messages": []}

        last_message = messages[-1]
        tool_calls = getattr(last_message, "tool_calls", None)
        if not tool_calls and isinstance(last_message, dict):
            tool_calls = last_message.get("tool_calls", [])

        if not tool_calls:
            return {"messages": []}

        output_messages: List[Dict[str, Any]] = []

        for call in tool_calls:
            call_id = call.get("id") if isinstance(call, dict) else getattr(call, "id", "call_default")
            tool_name = call.get("name") if isinstance(call, dict) else getattr(call, "name", "")
            tool_args = call.get("args") if isinstance(call, dict) else getattr(call, "args", {})
            if isinstance(tool_args, str):
                import json
                try:
                    tool_args = json.loads(tool_args)
                except Exception:
                    tool_args = {"raw": tool_args}

            tool_callable = self.tools_by_name.get(tool_name)
            if not tool_callable:
                output_messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": f"Error: Tool '{tool_name}' not found in registry",
                    "status": "error",
                })
                continue

            # Determine inverse action callable
            inverse_fn = None
            if tool_name in self.inverse_registry:
                try:
                    inverse_fn = self.inverse_registry[tool_name](tool_args)
                except Exception as e:
                    logger.warning("Failed to generate inverse for tool %s: %s", tool_name, e)

            # Determine target_id (heuristic: extracted from args or default)
            target_id = tool_args.get("target_id") or tool_args.get("node_id") or self.default_target_id

            try:
                # Synchronous Hypervisor Execution
                result, receipt = self.hypervisor.execute_guarded_tool(
                    agent_id=self.agent_id,
                    tool_name=tool_name,
                    target_id=str(target_id),
                    tool_func=tool_callable,
                    inverse_func=inverse_fn,
                    tool_kwargs=tool_args if isinstance(tool_args, dict) else {},
                )

                output_messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "name": tool_name,
                    "content": str(result),
                    "status": "success",
                    "receipt_hash": receipt.receipt_hash,
                })

            except (SecurityBreachBlockedError, BlastRadiusExceededError) as breach:
                logger.error("A2Z Hypervisor blocked tool call: %s", breach)
                output_messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "name": tool_name,
                    "content": f"BLOCKED BY A2Z AGENTIC HYPERVISOR: {breach}. Invariant tripwire engaged; state rolled back cleanly.",
                    "status": "blocked",
                })
            except Exception as exc:
                logger.error("Unhandled execution exception in tool %s: %s", tool_name, exc)
                output_messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "name": tool_name,
                    "content": f"Execution error in tool '{tool_name}': {exc}. Rollback executed.",
                    "status": "error",
                })

        return {"messages": output_messages}

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return self.invoke(state)
