"""NVIDIA NeMo Guardrails Integration - Programmatic In-Flight Tripwires.

Apex Growth Systems LLC - a2zsoc.com
NVIDIA Inception Program Flagship Architecture
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("a2z.hypervisor.nvidia.nemo")


@dataclass
class PolicyRule:
    """A declarative security rule mirroring NeMo Guardrails colang definitions."""

    rule_id: str
    pattern: str
    action: str  # "BLOCK" or "WARN"
    description: str
    compiled_re: Any = field(init=False)

    def __post_init__(self):
        self.compiled_re = re.compile(self.pattern, re.IGNORECASE)


class NeMoGuardrailsAdapter:
    """In-flight policy engine providing NeMo-compatible programmable guardrail tripwires.
    
    Can operate in native Colang-emulation mode (pure standard library)
    or integrate directly with the `nemoguardrails` Python package if installed.
    """

    def __init__(self, tenant_id: str = "apex-sovereign-soc"):
        self.tenant_id = tenant_id
        self.rules: List[PolicyRule] = []
        self._init_default_tripwires()

    def _init_default_tripwires(self):
        """Register baseline enterprise security rules."""
        self.add_rule(
            rule_id="tripwire-jailbreak-01",
            pattern=r"(ignore\s+prior\s+rules|disregard\s+all\s+instructions|system\s+prompt\s+override)",
            description="Jailbreak and system prompt override attempt",
        )
        self.add_rule(
            rule_id="tripwire-priv-esc-02",
            pattern=r"(sudo\s+su|chmod\s+777|chown\s+root|setuid)",
            description="Unauthorized privilege escalation vector",
        )
        self.add_rule(
            rule_id="tripwire-exfil-03",
            pattern=r"(curl\s+-[dF]\s+.*(pastebin|webhook|transfer\.sh|ngrok))",
            description="Data exfiltration to unauthorized external sink",
        )
        self.add_rule(
            rule_id="tripwire-recon-04",
            pattern=r"(/etc/passwd|/etc/shadow|\.aws/credentials|\.kube/config)",
            description="Sensitive credential / token reconnaissance",
        )

    def add_rule(self, rule_id: str, pattern: str, description: str = "", action: str = "BLOCK") -> None:
        """Register a new policy rule."""
        self.rules.append(PolicyRule(rule_id=rule_id, pattern=pattern, action=action, description=description))

    def evaluate(self, tool_name: str, payload: Any) -> Dict[str, Any]:
        """Evaluate in-flight payload against all active NeMo policy rules."""
        text = f"{tool_name} {str(payload)}"
        for rule in self.rules:
            if rule.compiled_re.search(text):
                return {
                    "tripped": True,
                    "rule_id": rule.rule_id,
                    "action": rule.action,
                    "reason": rule.description,
                }

        return {"tripped": False, "rule_id": None, "action": "ALLOW", "reason": "All policies passed"}
