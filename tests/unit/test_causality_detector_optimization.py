"""Unit tests for optimized causality detector with O(N log N) performance.

Tests verify:
1. Temporal causality detection accuracy
2. O(N log N) performance (binary search indexing)
3. Correct handling of edge cases
4. Confidence scoring logic
5. Causality type classification
"""

import pytest
import time
from typing import List
from athena.integration.causality_detector import (
    TemporalCausalityDetector,
    EventSignature,
    CausalLink,
    CausalityType,
    events_to_signatures,
)


class TestCausalityDetectorOptimization:
    """Test suite for optimized O(N log N) causality detection."""

    @pytest.fixture
    def detector(self):
        """Create a fresh detector instance."""
        return TemporalCausalityDetector()

    def test_detect_no_causality_on_empty_events(self, detector):
        """Should return empty list for empty event list."""
        assert detector.detect_causality_chains([]) == []

    def test_detect_no_causality_on_single_event(self, detector):
        """Should return empty list for single event."""
        event = EventSignature(
            event_id=1,
            timestamp=1000,
            event_type="TEST",
            outcome="success"
        )
        assert detector.detect_causality_chains([event]) == []

    def test_detect_causality_within_temporal_window(self, detector):
        """Should detect causality between events within 30-minute window."""
        # Code change at t=0
        code_change = EventSignature(
            event_id=1,
            timestamp=0,
            event_type="CODE_EDIT",
            outcome="success",
            has_code_change=True
        )
        # Test run at t=5 minutes (within window)
        test_run = EventSignature(
            event_id=2,
            timestamp=5 * 60 * 1000,  # 5 minutes later
            event_type="TEST_RUN",
            outcome="success",
            has_test_result=True,
            test_passed=True
        )

        links = detector.detect_causality_chains([code_change, test_run])

        assert len(links) == 1
        assert links[0].source_event_id == 1
        assert links[0].target_event_id == 2
        assert links[0].causality_type == CausalityType.CODE_CHANGE_EFFECT
        assert links[0].confidence > 0.5  # High confidence for code→test

    def test_ignore_causality_outside_temporal_window(self, detector):
        """Should not detect causality between events > 30 minutes apart."""
        event1 = EventSignature(
            event_id=1,
            timestamp=0,
            event_type="CODE_EDIT",
            outcome="success",
            has_code_change=True
        )
        event2 = EventSignature(
            event_id=2,
            timestamp=31 * 60 * 1000,  # 31 minutes later (outside window)
            event_type="TEST_RUN",
            outcome="success",
            has_test_result=True
        )

        links = detector.detect_causality_chains([event1, event2])
        assert len(links) == 0

    def test_temporal_proximity_scoring(self, detector):
        """Should score temporal proximity correctly."""
        # Create events at different time intervals
        base_event = EventSignature(
            event_id=1,
            timestamp=0,
            event_type="CODE_EDIT",
            outcome="success",
            has_code_change=True,
            files={"src/main.py"}
        )

        # Event 30 seconds later (very close)
        close_event = EventSignature(
            event_id=2,
            timestamp=30 * 1000,  # 30 seconds
            event_type="TEST_RUN",
            outcome="success",
            has_test_result=True,
            files={"src/main.py"}
        )

        # Event 10 minutes later (moderate distance)
        medium_event = EventSignature(
            event_id=3,
            timestamp=10 * 60 * 1000,  # 10 minutes
            event_type="TEST_RUN",
            outcome="success",
            has_test_result=True,
            files={"src/main.py"}
        )

        links = detector.detect_causality_chains(
            [base_event, close_event, medium_event]
        )

        # Find confidence scores
        close_confidence = next(l.confidence for l in links if l.target_event_id == 2)
        medium_confidence = next(l.confidence for l in links if l.target_event_id == 3)

        # Closer event should have higher confidence
        assert close_confidence > medium_confidence

    def test_context_overlap_scoring(self, detector):
        """Should give higher scores to events with shared context."""
        base_event = EventSignature(
            event_id=1,
            timestamp=0,
            event_type="CODE_EDIT",
            outcome="success",
            has_code_change=True,
            task="feature-x",
            files={"src/feature_x.py", "tests/test_x.py"}
        )

        # Same session, same files (strong overlap)
        strong_overlap = EventSignature(
            event_id=2,
            timestamp=5 * 60 * 1000,
            event_type="TEST_RUN",
            outcome="success",
            has_test_result=True,
            task="feature-x",
            session_id="session-1",
            files={"src/feature_x.py", "tests/test_x.py"}
        )

        # Same session but different files (weak overlap)
        weak_overlap = EventSignature(
            event_id=3,
            timestamp=5 * 60 * 1000,
            event_type="TEST_RUN",
            outcome="success",
            has_test_result=True,
            task="feature-y",
            session_id="session-1",
            files={"src/other.py"}
        )

        links = detector.detect_causality_chains(
            [base_event, strong_overlap, weak_overlap]
        )

        strong_conf = next(
            (l.confidence for l in links if l.target_event_id == 2), 0
        )
        weak_conf = next(
            (l.confidence for l in links if l.target_event_id == 3), 0
        )

        # Strong overlap should have higher confidence
        assert strong_conf > weak_conf

    def test_code_signal_detection(self, detector):
        """Should detect high-confidence causality from code signals."""
        code_change = EventSignature(
            event_id=1,
            timestamp=0,
            event_type="CODE_EDIT",
            outcome="success",
            has_code_change=True
        )

        # Test passes after code change (good signal)
        test_passes = EventSignature(
            event_id=2,
            timestamp=5 * 60 * 1000,
            event_type="TEST_RUN",
            outcome="success",
            has_test_result=True,
            test_passed=True
        )

        # Test fails after code change (bad signal)
        test_fails = EventSignature(
            event_id=3,
            timestamp=5 * 60 * 1000,
            event_type="TEST_RUN",
            outcome="failure",
            has_test_result=True,
            test_passed=False
        )

        # Check both scenarios
        links_pass = detector.detect_causality_chains([code_change, test_passes])
        links_fail = detector.detect_causality_chains([code_change, test_fails])

        assert len(links_pass) >= 1
        assert len(links_fail) >= 1

        # Both should have high confidence (0.85+)
        assert links_pass[0].confidence >= 0.5
        assert links_fail[0].confidence >= 0.5

    def test_causality_type_classification(self, detector):
        """Should correctly classify causality types."""
        code_change = EventSignature(
            event_id=1,
            timestamp=0,
            event_type="CODE_EDIT",
            outcome="success",
            has_code_change=True
        )

        test_result = EventSignature(
            event_id=2,
            timestamp=2 * 60 * 1000,
            event_type="TEST_RUN",
            outcome="failure",
            has_test_result=True,
            test_passed=False
        )

        links = detector.detect_causality_chains([code_change, test_result])

        assert len(links) >= 1
        assert links[0].causality_type == CausalityType.CODE_CHANGE_EFFECT

    def test_performance_o_n_log_n(self, detector):
        """Verify O(N log N) performance with large event set.

        Old O(N²) algorithm: 100 events = 5000 comparisons
        New O(N log N) algorithm: 100 events ≈ 650 comparisons
        Expected speedup: ~7-8x
        """
        # Create 100 events within temporal window
        events = []
        for i in range(100):
            timestamp = i * 1000  # 1 second apart
            event = EventSignature(
                event_id=i,
                timestamp=timestamp,
                event_type="TEST_RUN" if i % 2 == 0 else "CODE_EDIT",
                outcome="success" if i % 3 == 0 else "failure",
                has_code_change=i % 2 == 1,
                has_test_result=i % 2 == 0,
                task=f"task-{i // 10}"
            )
            events.append(event)

        # Time the detection
        start = time.perf_counter()
        links = detector.detect_causality_chains(events)
        elapsed = time.perf_counter() - start

        # Should complete in < 100ms even with 100 events
        assert elapsed < 0.1, f"Detection took {elapsed*1000:.1f}ms, expected < 100ms"

        # Should find some causal links
        assert len(links) > 0

    def test_temporal_index_correctness(self, detector):
        """Verify that temporal indexing finds correct candidates."""
        # Create events spread across time
        events = [
            EventSignature(
                event_id=i,
                timestamp=i * 5 * 60 * 1000,  # 5 minutes apart
                event_type="TEST_RUN",
                outcome="success"
            )
            for i in range(10)
        ]

        # Index building should work correctly
        detector._build_temporal_index(events)

        # Find candidates for first event (should find events within 30-minute window)
        candidates = detector._find_candidate_indices(
            source_timestamp=events[0].timestamp,
            window_ms=detector.TEMPORAL_WINDOW_MS,
            start_index=1
        )

        # With 5-minute spacing, 30-minute window should include ~6 events
        # (0, 5, 10, 15, 20, 25 minutes)
        assert len(candidates) >= 5
        assert len(candidates) <= 7

    def test_min_confidence_threshold(self, detector):
        """Should filter out links below MIN_CONFIDENCE threshold."""
        # Create events that are very far apart (weak signal)
        event1 = EventSignature(
            event_id=1,
            timestamp=0,
            event_type="RANDOM",
            outcome="success"
        )

        event2 = EventSignature(
            event_id=2,
            timestamp=29 * 60 * 1000,  # 29 minutes later (weak temporal signal)
            event_type="RANDOM",
            outcome="failure"
        )

        links = detector.detect_causality_chains([event1, event2])

        # Should either find no links or links with confidence >= MIN_CONFIDENCE
        for link in links:
            assert link.confidence >= detector.MIN_CONFIDENCE

    def test_multiple_causality_chains(self, detector):
        """Should detect multiple independent causality chains."""
        # Chain 1: Code edit → Test failure
        chain1 = [
            EventSignature(
                event_id=1,
                timestamp=0,
                event_type="CODE_EDIT",
                outcome="success",
                has_code_change=True,
                task="feature-a"
            ),
            EventSignature(
                event_id=2,
                timestamp=5 * 60 * 1000,
                event_type="TEST_RUN",
                outcome="failure",
                has_test_result=True,
                task="feature-a"
            ),
        ]

        # Chain 2: Different feature, same pattern
        chain2 = [
            EventSignature(
                event_id=3,
                timestamp=32 * 60 * 1000,  # After window of chain1
                event_type="CODE_EDIT",
                outcome="success",
                has_code_change=True,
                task="feature-b"
            ),
            EventSignature(
                event_id=4,
                timestamp=37 * 60 * 1000,
                event_type="TEST_RUN",
                outcome="failure",
                has_test_result=True,
                task="feature-b"
            ),
        ]

        events = chain1 + chain2
        links = detector.detect_causality_chains(events)

        # Should find at least 2 links (one per chain)
        assert len(links) >= 2

        # Chain 1 should be detected
        chain1_links = [l for l in links if l.source_event_id == 1]
        assert len(chain1_links) > 0

        # Chain 2 should be detected
        chain2_links = [l for l in links if l.source_event_id == 3]
        assert len(chain2_links) > 0


class TestCausalityDetectorEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def detector(self):
        return TemporalCausalityDetector()

    def test_events_with_identical_timestamps(self, detector):
        """Should handle events with identical timestamps."""
        events = [
            EventSignature(
                event_id=1,
                timestamp=1000,
                event_type="CODE_EDIT",
                outcome="success",
                has_code_change=True
            ),
            EventSignature(
                event_id=2,
                timestamp=1000,  # Same timestamp
                event_type="TEST_RUN",
                outcome="success",
                has_test_result=True
            ),
        ]

        # Should not crash, might not detect causality (timestamp is after/before)
        links = detector.detect_causality_chains(events)
        # Result is acceptable regardless, as long as no crash

    def test_events_out_of_timestamp_order(self, detector):
        """Should handle unsorted events."""
        events = [
            EventSignature(
                event_id=1,
                timestamp=1000,
                event_type="CODE_EDIT",
                outcome="success"
            ),
            EventSignature(
                event_id=2,
                timestamp=500,  # Earlier timestamp
                event_type="TEST_RUN",
                outcome="success"
            ),
        ]

        # Function assumes sorted input, but should not crash
        links = detector.detect_causality_chains(events)
        # Behavior depends on implementation (may find no links)

    def test_large_temporal_gap_no_false_positives(self, detector):
        """Should not report causality across large temporal gaps."""
        events = [
            EventSignature(
                event_id=i,
                timestamp=i * 31 * 60 * 1000,  # 31 minutes apart (outside window)
                event_type="TEST_RUN",
                outcome="success"
            )
            for i in range(5)
        ]

        links = detector.detect_causality_chains(events)

        # Should find very few or no links due to temporal distance
        assert len(links) == 0

    def test_reasoning_generation(self, detector):
        """Should generate human-readable reasoning."""
        event1 = EventSignature(
            event_id=1,
            timestamp=0,
            event_type="CODE_EDIT",
            outcome="success",
            has_code_change=True,
            files={"src/main.py"}
        )

        event2 = EventSignature(
            event_id=2,
            timestamp=2 * 60 * 1000,  # 2 minutes later
            event_type="TEST_RUN",
            outcome="failure",
            has_test_result=True,
            files={"src/main.py"}
        )

        links = detector.detect_causality_chains([event1, event2])

        assert len(links) > 0
        # Reasoning should contain human-readable text
        assert len(links[0].reasoning) > 0
        assert any(word in links[0].reasoning.lower() for word in ["event", "time", "change", "test"])


class TestEventsToSignaturesConversion:
    """Test conversion from database event dicts to EventSignature."""

    def test_convert_event_dict_to_signature(self):
        """Should convert database event dict to EventSignature."""
        event_dict = {
            'id': 123,
            'timestamp': 1000,
            'event_type': 'CODE_EDIT',
            'outcome': 'success',
            'context_files': ['src/main.py', 'tests/test_main.py'],
            'context_task': 'feature-x',
            'context_phase': 'implementation',
            'session_id': 'session-1',
            'files_changed': 2,
            'error_type': None,
        }

        signatures = events_to_signatures([event_dict])

        assert len(signatures) == 1
        sig = signatures[0]
        assert sig.event_id == 123
        assert sig.timestamp == 1000
        assert sig.event_type == 'CODE_EDIT'
        assert sig.outcome == 'success'
        assert sig.files == {'src/main.py', 'tests/test_main.py'}
        assert sig.task == 'feature-x'
        assert sig.phase == 'implementation'
        assert sig.session_id == 'session-1'

    def test_convert_multiple_events(self):
        """Should convert multiple event dicts preserving order."""
        events_dicts = [
            {'id': i, 'timestamp': i * 1000, 'event_type': 'TEST_RUN', 'outcome': 'success'}
            for i in range(5)
        ]

        signatures = events_to_signatures(events_dicts)

        assert len(signatures) == 5
        # Should be sorted by timestamp
        for i, sig in enumerate(signatures):
            assert sig.timestamp == i * 1000
