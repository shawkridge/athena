"""Unit tests for temporal chain system."""

import pytest
from datetime import datetime, timedelta

from athena.episodic.models import EpisodicEvent, EventContext, EventType
from athena.temporal.chains import (
    calculate_causal_strength,
    create_temporal_chains,
    create_temporal_relations,
    detect_causal_patterns,
    infer_causal_relations,
    is_likely_causal,
)
from athena.temporal.models import CausalPattern, EventChain, TemporalRelation


def create_test_event(
    event_id: int,
    session_id: str,
    event_type: EventType,
    timestamp: datetime,
    outcome: str = "success",
    content: str = "Test event",
    files: list = None
) -> EpisodicEvent:
    """Helper to create test events."""
    return EpisodicEvent(
        id=event_id,
        project_id=1,
        session_id=session_id,
        event_type=event_type,
        content=content,
        outcome=outcome,
        timestamp=timestamp,
        context=EventContext(cwd="/project/src", files=files or [])
    )


class TestTemporalChains:
    """Test temporal chain creation."""

    def test_create_chains_single_session(self):
        """Test creating chains from events in single session."""
        base_time = datetime.now()
        events = [
            create_test_event(1, "sess1", EventType.ACTION, base_time),
            create_test_event(2, "sess1", EventType.FILE_CHANGE, base_time + timedelta(minutes=5)),
            create_test_event(3, "sess1", EventType.TEST_RUN, base_time + timedelta(minutes=10)),
        ]

        chains = create_temporal_chains(events, same_session_only=True)

        assert len(chains) == 1
        assert len(chains[0].events) == 3
        assert chains[0].chain_type == 'temporal'
        assert chains[0].session_id == "sess1"

    def test_create_chains_breaks_on_time_gap(self):
        """Test chain breaks after 1 hour gap."""
        base_time = datetime.now()
        events = [
            create_test_event(1, "sess1", EventType.ACTION, base_time),
            create_test_event(2, "sess1", EventType.FILE_CHANGE, base_time + timedelta(minutes=5)),
            # 2 hour gap
            create_test_event(3, "sess1", EventType.TEST_RUN, base_time + timedelta(hours=2)),
        ]

        chains = create_temporal_chains(events, same_session_only=True)

        # Should create 1 chain from first 2 events (3rd event is too far)
        assert len(chains) == 1
        assert len(chains[0].events) == 2

    def test_create_chains_multiple_sessions(self):
        """Test chains across multiple sessions."""
        base_time = datetime.now()
        events = [
            create_test_event(1, "sess1", EventType.ACTION, base_time),
            create_test_event(2, "sess1", EventType.FILE_CHANGE, base_time + timedelta(minutes=5)),
            create_test_event(3, "sess2", EventType.ACTION, base_time + timedelta(minutes=10)),
            create_test_event(4, "sess2", EventType.TEST_RUN, base_time + timedelta(minutes=15)),
        ]

        # With same_session_only=False, should bridge sessions
        chains = create_temporal_chains(events, same_session_only=False)

        assert len(chains) == 1
        assert len(chains[0].events) == 4

    def test_empty_events_list(self):
        """Test handling empty events list."""
        chains = create_temporal_chains([])
        assert chains == []


class TestTemporalRelations:
    """Test temporal relation creation."""

    def test_immediately_after_relation(self):
        """Test 'immediately_after' for events < 60s apart."""
        base_time = datetime.now()
        events = [
            create_test_event(1, "sess1", EventType.ACTION, base_time),
            create_test_event(2, "sess1", EventType.FILE_CHANGE, base_time + timedelta(seconds=30)),
        ]

        relations = create_temporal_relations(events)

        assert len(relations) == 1
        assert relations[0].relation_type == 'immediately_after'
        assert relations[0].strength == 0.9

    def test_shortly_after_relation(self):
        """Test 'shortly_after' for events < 1 hour apart."""
        base_time = datetime.now()
        events = [
            create_test_event(1, "sess1", EventType.ACTION, base_time),
            create_test_event(2, "sess1", EventType.FILE_CHANGE, base_time + timedelta(minutes=30)),
        ]

        relations = create_temporal_relations(events)

        assert len(relations) == 1
        assert relations[0].relation_type == 'shortly_after'
        assert relations[0].strength == 0.7

    def test_later_after_relation(self):
        """Test 'later_after' for events > 1 hour apart."""
        base_time = datetime.now()
        events = [
            create_test_event(1, "sess1", EventType.ACTION, base_time),
            create_test_event(2, "sess1", EventType.FILE_CHANGE, base_time + timedelta(hours=2)),
        ]

        relations = create_temporal_relations(events)

        assert len(relations) == 1
        assert relations[0].relation_type == 'later_after'
        assert 0.3 <= relations[0].strength <= 0.9


class TestCausalInference:
    """Test causal relationship inference."""

    def test_error_fix_causality(self):
        """Test error followed by fix is detected as causal."""
        base_time = datetime.now()
        error_event = create_test_event(
            1, "sess1", EventType.ERROR, base_time,
            content="NullPointerException in auth.py",
            files=["auth.py"]
        )
        fix_event = create_test_event(
            2, "sess1", EventType.FILE_CHANGE, base_time + timedelta(minutes=5),
            content="Fixed null check in auth.py",
            files=["auth.py"]
        )

        assert is_likely_causal(error_event, fix_event) is True

    def test_tdd_causality(self):
        """Test TDD pattern is detected as causal."""
        base_time = datetime.now()
        test_fail = create_test_event(
            1, "sess1", EventType.TEST_RUN, base_time,
            outcome="failure"
        )
        code_change = create_test_event(
            2, "sess1", EventType.FILE_CHANGE, base_time + timedelta(minutes=2)
        )

        assert is_likely_causal(test_fail, code_change) is True

    def test_decision_action_causality(self):
        """Test decision followed by action is detected as causal."""
        base_time = datetime.now()
        decision = create_test_event(
            1, "sess1", EventType.DECISION, base_time,
            content="Decided to use JWT for auth"
        )
        action = create_test_event(
            2, "sess1", EventType.ACTION, base_time + timedelta(minutes=1),
            content="Implemented JWT authentication"
        )

        assert is_likely_causal(decision, action) is True

    def test_no_causality_unrelated_events(self):
        """Test unrelated events are not causal."""
        base_time = datetime.now()
        event1 = create_test_event(1, "sess1", EventType.ACTION, base_time)
        event2 = create_test_event(2, "sess1", EventType.ACTION, base_time + timedelta(minutes=5))

        assert is_likely_causal(event1, event2) is False

    def test_infer_causal_relations(self):
        """Test inferring causal relations from event sequence."""
        base_time = datetime.now()
        events = [
            create_test_event(1, "sess1", EventType.ERROR, base_time, files=["auth.py"]),
            create_test_event(2, "sess1", EventType.FILE_CHANGE, base_time + timedelta(minutes=2), files=["auth.py"]),
            create_test_event(3, "sess1", EventType.SUCCESS, base_time + timedelta(minutes=5)),
        ]

        causal_relations = infer_causal_relations(events)

        assert len(causal_relations) >= 1
        assert any(r.relation_type == 'caused' for r in causal_relations)

    def test_causal_strength_calculation(self):
        """Test causal strength calculation."""
        base_time = datetime.now()
        event1 = create_test_event(
            1, "sess1", EventType.ERROR, base_time,
            files=["auth.py", "user.py"]
        )
        event2 = create_test_event(
            2, "sess1", EventType.FILE_CHANGE, base_time + timedelta(seconds=30),
            files=["auth.py"]
        )

        strength = calculate_causal_strength(event1, event2)

        # Should be high due to: time proximity, file overlap, same session
        assert strength > 0.7


class TestCausalPatterns:
    """Test causal pattern detection."""

    def test_detect_tdd_pattern(self):
        """Test detection of TDD cycle pattern."""
        base_time = datetime.now()
        events = [
            create_test_event(1, "sess1", EventType.TEST_RUN, base_time, outcome="failure"),
            create_test_event(2, "sess1", EventType.FILE_CHANGE, base_time + timedelta(minutes=2)),
            create_test_event(3, "sess1", EventType.TEST_RUN, base_time + timedelta(minutes=5), outcome="success"),
        ]

        patterns = detect_causal_patterns(events)

        assert len(patterns) >= 1
        tdd_patterns = [p for p in patterns if p.pattern_type == 'tdd_cycle']
        assert len(tdd_patterns) == 1
        assert tdd_patterns[0].confidence >= 0.75

    def test_detect_error_fix_pattern(self):
        """Test detection of error recovery pattern."""
        base_time = datetime.now()
        events = [
            create_test_event(1, "sess1", EventType.ERROR, base_time),
            create_test_event(2, "sess1", EventType.FILE_CHANGE, base_time + timedelta(minutes=3)),
            create_test_event(3, "sess1", EventType.SUCCESS, base_time + timedelta(minutes=6)),
        ]

        patterns = detect_causal_patterns(events)

        assert len(patterns) >= 1
        error_fix = [p for p in patterns if p.pattern_type == 'error_fix']
        assert len(error_fix) == 1

    def test_detect_debug_session_pattern(self):
        """Test detection of debugging session."""
        base_time = datetime.now()
        events = [
            create_test_event(1, "sess1", EventType.ERROR, base_time),
            create_test_event(2, "sess1", EventType.DEBUGGING, base_time + timedelta(minutes=2)),
            create_test_event(3, "sess1", EventType.ERROR, base_time + timedelta(minutes=5)),
            create_test_event(4, "sess1", EventType.SUCCESS, base_time + timedelta(minutes=10)),
        ]

        patterns = detect_causal_patterns(events)

        debug_sessions = [p for p in patterns if p.pattern_type == 'debug_session']
        assert len(debug_sessions) >= 1
        assert len(debug_sessions[0].events) >= 3

    def test_no_patterns_for_short_sequence(self):
        """Test no patterns detected for sequences < 3 events."""
        base_time = datetime.now()
        events = [
            create_test_event(1, "sess1", EventType.ACTION, base_time),
            create_test_event(2, "sess1", EventType.FILE_CHANGE, base_time + timedelta(minutes=2)),
        ]

        patterns = detect_causal_patterns(events)
        assert patterns == []


class TestTemporalModels:
    """Test temporal model data structures."""

    def test_temporal_relation_validation(self):
        """Test TemporalRelation validates fields."""
        # Valid relation
        relation = TemporalRelation(
            from_event_id=1,
            to_event_id=2,
            relation_type='immediately_after',
            strength=0.9,
            inferred_at=datetime.now()
        )
        assert relation.strength == 0.9

        # Invalid relation type
        with pytest.raises(ValueError):
            TemporalRelation(1, 2, 'invalid_type', 0.9, datetime.now())

        # Invalid strength
        with pytest.raises(ValueError):
            TemporalRelation(1, 2, 'caused', 1.5, datetime.now())

    def test_event_chain_properties(self):
        """Test EventChain properties."""
        base_time = datetime.now()
        events = [
            create_test_event(1, "sess1", EventType.ACTION, base_time),
            create_test_event(2, "sess1", EventType.FILE_CHANGE, base_time + timedelta(minutes=5)),
        ]

        chain = EventChain(
            events=events,
            chain_type='temporal',
            start_time=base_time,
            end_time=base_time + timedelta(minutes=5),
            session_id="sess1"
        )

        assert len(chain) == 2
        assert chain.duration_seconds == 300.0

    def test_causal_pattern_validation(self):
        """Test CausalPattern validates confidence."""
        base_time = datetime.now()
        events = [create_test_event(1, "sess1", EventType.ACTION, base_time)]

        # Valid pattern
        pattern = CausalPattern(
            pattern_type='tdd_cycle',
            events=events,
            confidence=0.85,
            description="Test pattern"
        )
        assert pattern.confidence == 0.85

        # Invalid confidence
        with pytest.raises(ValueError):
            CausalPattern('tdd_cycle', events, 1.2, "Invalid")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
