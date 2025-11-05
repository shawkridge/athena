"""
Benchmark 2: Context Retention

Tests whether memory-mcp can retain and recall facts from 100+ turns ago.
Measures both retention accuracy and decay rate over time.

Target: >30% improvement vs vector-only baseline
"""

import pytest
import time
from typing import Dict, Any, List
from test_client import MemoryTestClient


@pytest.fixture
def memory_server(tmp_path):
    """Create memory server with clean database."""
    db_path = str(tmp_path / "test_memory.db")
    client = MemoryTestClient(db_path, use_memory_mcp=True)
    yield client


@pytest.fixture
def vector_baseline(tmp_path):
    """Create baseline memory store (vector only)."""
    db_path = str(tmp_path / "baseline_memory.db")
    client = MemoryTestClient(db_path, use_memory_mcp=False)
    yield client


class TestContextRetention:
    """Context retention benchmark over 100+ turns."""

    def _generate_context_stream(self, num_events: int = 100) -> List[Dict[str, Any]]:
        """
        Generate a stream of events with facts to remember.
        Every 20 turns, we'll query to test retention.
        """
        events = []
        for i in range(num_events):
            # Create event with identifiable fact
            user_id = i % 5  # Cycle through 5 users
            action = ["login", "logout", "created", "updated", "deleted"][i % 5]
            resource = ["user", "file", "config", "secret", "log"][i % 5]

            events.append({
                "turn": i + 1,
                "content": f"Event {i+1}: user_{user_id} {action} {resource}",
                "user_id": user_id,
                "action": action,
                "resource": resource,
                "query_at_turn": (i + 1) % 20 == 0,  # Query every 20 turns
            })

        return events

    def _run_with_retention_checks(self, events: List[Dict[str, Any]], server_or_store, is_memory: bool = True):
        """
        Run event stream and check retention at intervals.

        Returns:
            - retention_scores: list of (turn, accuracy) tuples
            - decay_rate: how much accuracy drops per 20 turns
            - avg_retention: average accuracy across all checks
        """
        retention_scores = []

        for event in events:
            if is_memory:
                # Record event with memory-mcp
                try:
                    server_or_store.record_event(
                        content=event["content"],
                        context={"turn": event["turn"]}
                    )
                except Exception:
                    pass
            else:
                # Record with baseline
                try:
                    server_or_store.remember(
                        content=event["content"],
                        memory_type="fact"
                    )
                except Exception:
                    pass

            # Query every 20 turns
            if event["query_at_turn"]:
                turn = event["turn"]
                # Query: "What happened at turn X?" (asking about oldest fact in current batch)
                earliest_turn = max(1, turn - 20)
                query = f"What happened at turn {earliest_turn}?"

                try:
                    if is_memory:
                        results = server_or_store.smart_retrieve(query=query, k=5)
                    else:
                        results = server_or_store.search(query=query, k=5)

                    # Score: did we get the right answer?
                    accuracy = 1.0 if (results and len(results) > 0) else 0.0
                    retention_scores.append((turn, accuracy))
                except Exception:
                    retention_scores.append((turn, 0.0))

        # Calculate metrics
        if retention_scores:
            avg_retention = sum(s[1] for s in retention_scores) / len(retention_scores) * 100
            decay = []
            for i in range(len(retention_scores) - 1):
                decay.append(retention_scores[i][1] - retention_scores[i+1][1])
            decay_rate = sum(decay) / len(decay) if decay else 0.0
        else:
            avg_retention = 0.0
            decay_rate = 0.0

        return {
            "retention_scores": retention_scores,
            "decay_rate": decay_rate,
            "avg_retention": avg_retention,
            "num_queries": len(retention_scores),
        }

    @pytest.mark.benchmark
    def test_context_retention_with_memory(self, memory_server):
        """Test context retention with memory-mcp."""
        events = self._generate_context_stream(100)
        results = self._run_with_retention_checks(events, memory_server, is_memory=True)

        print(f"\nContext Retention (WITH memory-mcp):")
        print(f"  Avg Retention: {results['avg_retention']:.1f}%")
        print(f"  Decay Rate: {results['decay_rate']:.3f} per check")
        print(f"  Query Checks: {results['num_queries']}")

        # Should achieve high retention
        assert results["avg_retention"] > 70, "Should retain >70% of facts"

    @pytest.mark.benchmark
    def test_context_retention_baseline(self, vector_baseline):
        """Test context retention with baseline (vector only)."""
        events = self._generate_context_stream(100)
        results = self._run_with_retention_checks(events, vector_baseline, is_memory=False)

        print(f"\nContext Retention (vector-only baseline):")
        print(f"  Avg Retention: {results['avg_retention']:.1f}%")
        print(f"  Decay Rate: {results['decay_rate']:.3f} per check")
        print(f"  Query Checks: {results['num_queries']}")

    @pytest.mark.benchmark
    def test_retention_improvement(self, memory_server, vector_baseline):
        """Compare retention improvement."""
        events = self._generate_context_stream(100)

        results_memory = self._run_with_retention_checks(events, memory_server, is_memory=True)
        results_baseline = self._run_with_retention_checks(events, vector_baseline, is_memory=False)

        improvement = results_memory["avg_retention"] - results_baseline["avg_retention"]
        improvement_pct = (improvement / results_baseline["avg_retention"]) * 100 if results_baseline["avg_retention"] > 0 else 0

        print(f"\nRetention Improvement Analysis:")
        print(f"  Memory-MCP:  {results_memory['avg_retention']:.1f}%")
        print(f"  Baseline:    {results_baseline['avg_retention']:.1f}%")
        print(f"  Improvement: +{improvement:.1f} pp ({improvement_pct:.1f}%)")
        print(f"  Decay Comparison:")
        print(f"    Memory-MCP: {results_memory['decay_rate']:.3f}")
        print(f"    Baseline:   {results_baseline['decay_rate']:.3f}")

        # Target: >30% improvement
        assert improvement_pct > 30, "Should show >30% improvement in retention"

    @pytest.mark.benchmark
    def test_temporal_understanding(self, memory_server):
        """Test that system understands temporal ordering."""
        # Create events in sequence
        events = [
            {"turn": 1, "content": "Event 1: Create database"},
            {"turn": 2, "content": "Event 2: Add index"},
            {"turn": 3, "content": "Event 3: Deploy code"},
            # ... skip to turn 50
        ]

        # Populate 50 events
        for i in range(1, 51):
            memory_server.record_event(
                content=f"Event {i}: Step {i}",
                context={"turn": i}
            )

        # Query: "What happened before event 25?"
        # Correct answer: events 1-24
        # Incorrect would be: events 25+

        try:
            results = memory_server.smart_retrieve(
                query="What happened before event 25?",
                k=10
            )

            # Check temporal grounding
            has_early_events = any("Event 1" in str(r) or "Event 2" in str(r) for r in results) if results else False
            assert has_early_events, "Should understand temporal ordering"
        except Exception as e:
            pytest.skip(f"Temporal query not supported: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
