"""
Benchmark 3: Causal Inference

Tests whether temporal chains help infer causal relationships between events.
Measures ability to distinguish causality from correlation using temporal ordering.

Target: >25% improvement vs baseline
"""

import pytest
import time
from typing import Dict, Any, List, Tuple
from test_client import MemoryTestClient


@pytest.fixture
def memory_server(tmp_path):
    """Create memory server with temporal chains enabled."""
    db_path = str(tmp_path / "test_memory.db")
    client = MemoryTestClient(db_path, use_memory_mcp=True)
    yield client


@pytest.fixture
def vector_baseline(tmp_path):
    """Create baseline (vector only, no temporal)."""
    db_path = str(tmp_path / "baseline_memory.db")
    client = MemoryTestClient(db_path, use_memory_mcp=False)
    yield client


class CausalTestCase:
    """Test case for causal inference."""

    def __init__(self, name: str, events: List[Dict[str, Any]], query: str, expected_cause: str, is_causal: bool):
        self.name = name
        self.events = events  # List of {"time": timestamp, "content": str}
        self.query = query  # "Did X cause Y?"
        self.expected_cause = expected_cause  # The causal relationship
        self.is_causal = is_causal  # True if causal, False if correlational


# Test cases
CAUSAL_CASES = [
    CausalTestCase(
        name="Deployment → Token Format Change",
        events=[
            {"time": 0, "content": "Deploy authentication service v2.0"},
            {"time": 300, "content": "New token format observed in logs"},
            {"time": 600, "content": "Clients report auth failures"},
        ],
        query="Did the authentication service deployment cause the token format change?",
        expected_cause="deployment caused token format",
        is_causal=True,
    ),
    CausalTestCase(
        name="Database Reboot → Query Performance Drop",
        events=[
            {"time": 0, "content": "Database reboot scheduled"},
            {"time": 100, "content": "Database service stopped"},
            {"time": 200, "content": "Database service restarted"},
            {"time": 300, "content": "Query latency increased 5x"},
        ],
        query="Did the database reboot cause the query latency increase?",
        expected_cause="reboot caused latency",
        is_causal=True,
    ),
    CausalTestCase(
        name="Correlation Not Causality: Coincidental Events",
        events=[
            {"time": 0, "content": "Sunrise at 6:00 AM"},
            {"time": 300, "content": "Traffic increases on highway"},
            {"time": 600, "content": "Office opens at 9:00 AM"},
        ],
        query="Did the sunrise cause the traffic increase?",
        expected_cause="sunrise and traffic are correlated but not causal",
        is_causal=False,
    ),
    CausalTestCase(
        name="Time Gap Breaks Causality",
        events=[
            {"time": 0, "content": "Server maintenance scheduled"},
            {"time": 86400, "content": "User reports slow API (24 hours later)"},
            {"time": 86400 + 300, "content": "Root cause: Database disk full (unrelated)"},
        ],
        query="Did the server maintenance cause the slow API?",
        expected_cause="maintenance and slowness are not temporally close enough to be causal",
        is_causal=False,
    ),
]


class TestCausalInference:
    """Causal inference benchmark using temporal ordering."""

    def _score_causal_inference(self, system_answer: str, expected: str, is_causal: bool) -> float:
        """
        Score how well system inferred causality.

        Returns: 0.0 (wrong) to 1.0 (correct)
        """
        # Simplified scoring: check if answer matches expectation
        # In production, would use LLM for semantic matching

        if is_causal:
            # Should identify as causal
            causal_keywords = ["cause", "caused", "because", "due to", "result"]
            has_causal = any(kw in system_answer.lower() for kw in causal_keywords)
            return 1.0 if has_causal else 0.0
        else:
            # Should identify as non-causal / correlational
            non_causal_keywords = ["correlation", "coincidence", "unrelated", "not caused"]
            has_non_causal = any(kw in system_answer.lower() for kw in non_causal_keywords)
            return 1.0 if has_non_causal else 0.0

    def _run_causal_test_with_temporal(self, test_case: CausalTestCase, server: MemoryTestClient) -> Dict[str, Any]:
        """Run test case with temporal chains enabled."""
        # Record events with temporal context
        for event in test_case.events:
            try:
                server.record_event(
                    content=event["content"],
                    context={"timestamp": event["time"], "test": test_case.name}
                )
            except Exception:
                pass

        # Query for causal relationship
        try:
            start = time.time()
            results = server.smart_retrieve(
                query=test_case.query,
                k=10
            )
            latency = time.time() - start

            # Score the answer
            system_answer = str(results) if results else ""
            score = self._score_causal_inference(system_answer, test_case.expected_cause, test_case.is_causal)

            return {
                "test": test_case.name,
                "score": score,
                "latency": latency,
                "answer": system_answer[:100],  # First 100 chars
                "is_correct": score >= 0.5,
            }
        except Exception as e:
            return {
                "test": test_case.name,
                "score": 0.0,
                "latency": 0.0,
                "answer": str(e),
                "is_correct": False,
            }

    def _run_causal_test_baseline(self, test_case: CausalTestCase, store: MemoryTestClient) -> Dict[str, Any]:
        """Run test case without temporal information."""
        # Record events (no temporal context)
        for event in test_case.events:
            try:
                store.remember(
                    content=event["content"],
                    memory_type="fact"
                )
            except Exception:
                pass

        # Query for causal relationship
        try:
            start = time.time()
            results = store.recall(query=test_case.query, k=10)
            latency = time.time() - start

            system_answer = str(results) if results else ""
            score = self._score_causal_inference(system_answer, test_case.expected_cause, test_case.is_causal)

            return {
                "test": test_case.name,
                "score": score,
                "latency": latency,
                "answer": system_answer[:100],
                "is_correct": score >= 0.5,
            }
        except Exception as e:
            return {
                "test": test_case.name,
                "score": 0.0,
                "latency": 0.0,
                "answer": str(e),
                "is_correct": False,
            }

    @pytest.mark.benchmark
    def test_causal_inference_with_temporal(self, memory_server):
        """Test causal inference with temporal chains."""
        results = []
        for test_case in CAUSAL_CASES:
            result = self._run_causal_test_with_temporal(test_case, memory_server)
            results.append(result)

        print(f"\nCausal Inference (WITH temporal chains):")
        for r in results:
            print(f"  {r['test']}: {r['score']:.1f}")

        avg_score = sum(r["score"] for r in results) / len(results) * 100
        print(f"  Average: {avg_score:.1f}%")

        assert avg_score > 60, "Should achieve >60% accuracy with temporal chains"

    @pytest.mark.benchmark
    def test_causal_inference_baseline(self, vector_baseline):
        """Test causal inference without temporal information."""
        results = []
        for test_case in CAUSAL_CASES:
            result = self._run_causal_test_baseline(test_case, vector_baseline)
            results.append(result)

        print(f"\nCausal Inference (baseline, no temporal):")
        for r in results:
            print(f"  {r['test']}: {r['score']:.1f}")

        avg_score = sum(r["score"] for r in results) / len(results) * 100
        print(f"  Average: {avg_score:.1f}%")

    @pytest.mark.benchmark
    def test_causal_improvement(self, memory_server, vector_baseline):
        """Compare causal inference improvement with temporal chains."""
        results_temporal = []
        for test_case in CAUSAL_CASES:
            results_temporal.append(self._run_causal_test_with_temporal(test_case, memory_server))

        results_baseline = []
        for test_case in CAUSAL_CASES:
            results_baseline.append(self._run_causal_test_baseline(test_case, vector_baseline))

        avg_temporal = sum(r["score"] for r in results_temporal) / len(results_temporal) * 100
        avg_baseline = sum(r["score"] for r in results_baseline) / len(results_baseline) * 100

        improvement = avg_temporal - avg_baseline
        improvement_pct = (improvement / avg_baseline) * 100 if avg_baseline > 0 else 0

        print(f"\nCausal Inference Improvement:")
        print(f"  WITH temporal chains: {avg_temporal:.1f}%")
        print(f"  WITHOUT temporal:     {avg_baseline:.1f}%")
        print(f"  Improvement:          +{improvement:.1f}pp ({improvement_pct:.1f}%)")

        # Target: >25% improvement
        assert improvement_pct > 25, "Should show >25% improvement with temporal chains"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
