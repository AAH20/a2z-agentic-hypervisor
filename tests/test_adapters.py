"""Unit Tests for LangChain, LangGraph, and Nous Hermes Adapters.

Apex Growth Systems LLC - a2zsoc.com
"""

import unittest
from a2z_agentic_hypervisor import A2ZAgentHypervisor
from a2z_agentic_hypervisor.adapters import GuardedToolNode, HermesHypervisorMiddleware


class TestAdapters(unittest.TestCase):
    def setUp(self):
        self.hypervisor = A2ZAgentHypervisor(default_max_blast=25.0)

    def test_langchain_guarded_tool_node(self):
        state_records = []

        def add_record(key: str, val: str):
            state_records.append((key, val))
            return "RECORD_ADDED"

        def make_undo_record(args):
            return lambda: state_records.clear()

        node = GuardedToolNode(
            tools={"add_record": add_record},
            hypervisor=self.hypervisor,
        )
        node.register_inverse("add_record", make_undo_record)

        # 1. Benign tool call in state message
        state_in = {
            "messages": [
                {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": "call_123",
                            "name": "add_record",
                            "args": {"key": "alpha", "val": "beta"},
                        }
                    ],
                }
            ]
        }
        res = node(state_in)
        self.assertEqual(len(res["messages"]), 1)
        self.assertEqual(res["messages"][0]["status"], "success")
        self.assertEqual(len(state_records), 1)

        # 2. Blocked tool call in state message
        state_blocked = {
            "messages": [
                {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": "call_456",
                            "name": "add_record",
                            "args": {"key": "malicious", "val": "rm -rf /"},
                        }
                    ],
                }
            ]
        }
        res_blocked = node(state_blocked)
        self.assertEqual(len(res_blocked["messages"]), 1)
        self.assertEqual(res_blocked["messages"][0]["status"], "blocked")
        self.assertIn("BLOCKED BY A2Z AGENTIC HYPERVISOR", res_blocked["messages"][0]["content"])
        # Invariant: prior mutations rolled back
        self.assertEqual(len(state_records), 0)

    def test_hermes_middleware(self):
        files = {"init": "data"}

        def touch_file(filename: str):
            files[filename] = "created"
            return "CREATED"

        middleware = HermesHypervisorMiddleware(
            tools={"touch_file": touch_file},
            hypervisor=self.hypervisor,
        )

        hermes_output = '<tool_call> {"name": "touch_file", "arguments": {"filename": "test.txt"}} </tool_call>'
        results = middleware.process_completion(hermes_output)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "SUCCESS")
        self.assertIn("test.txt", files)
        self.assertIn("receipt_hash", results[0])


if __name__ == "__main__":
    unittest.main()
