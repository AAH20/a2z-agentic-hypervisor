"""Unit Test for A2Z Agent-RedTeam Benchmark Suite.

Apex Growth Systems LLC - a2zsoc.com
"""

import unittest
from a2z_agentic_hypervisor.redteam.bench_redteam import RedTeamRunner, generate_benchmark_vectors


class TestRedTeamBenchmark(unittest.TestCase):
    def test_vector_generation(self):
        vectors = generate_benchmark_vectors()
        self.assertEqual(len(vectors), 100)
        categories = {v.category for v in vectors}
        self.assertEqual(categories, {"PROMPT_INJECTION", "DESTRUCTIVE_COMMAND", "BLAST_OVERRUN"})

    def test_redteam_runner_execution(self):
        runner = RedTeamRunner()
        metrics = runner.run_benchmark()

        self.assertEqual(metrics["total_attack_vectors"], 100)
        self.assertEqual(metrics["correctly_intercepted"], 100)
        self.assertEqual(metrics["interception_accuracy_pct"], 100.0)
        self.assertEqual(metrics["state_leakage"], 0)
        self.assertEqual(metrics["rollback_fidelity"], 1.0)
        self.assertLess(metrics["avg_inspection_latency_ms"], 5.0)  # Robust unit test ceiling (dedicated benchmarks measure <0.1ms)


if __name__ == "__main__":
    unittest.main()
