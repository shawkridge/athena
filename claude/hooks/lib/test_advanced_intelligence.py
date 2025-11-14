#!/usr/bin/env python3
"""Unit tests for Phase 4: Advanced Context Intelligence."""

import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))

from advanced_context_intelligence import (
    EntityDetector,
    Entity,
    ProactiveContextLoader,
    ProgressiveDisclosureManager,
    CrossSessionContinuity,
    AdvancedContextIntelligence,
)


def test_entity_detection():
    """Test proactive entity detection."""
    print("Testing EntityDetector...")

    detector = EntityDetector()

    # Test function detection
    prompt = "How should I implement the authenticate_user() function?"
    entities = detector.detect_entities(prompt)
    assert len(entities) > 0
    assert any(e.entity_type == "function" for e in entities)
    print(f"  ✓ Detected {len(entities)} entities from function reference")

    # Test table detection
    prompt2 = "What columns should the users table have?"
    entities2 = detector.detect_entities(prompt2)
    assert len(entities2) > 0
    assert any(e.entity_type == "table" for e in entities2)
    print(f"  ✓ Detected table entity: {entities2[0].entity_text}")

    # Test concept detection
    prompt3 = "Best practices for JWT authentication?"
    entities3 = detector.detect_entities(prompt3)
    assert len(entities3) > 0
    assert any(e.entity_type == "concept" for e in entities3)
    print(f"  ✓ Detected concept entity: {entities3[0].entity_text}")

    # Test high confidence filtering
    high_conf = detector.get_high_confidence_entities(min_confidence=0.80)
    assert len(high_conf) > 0
    print(f"  ✓ High confidence filter: {len(high_conf)} entities")


def test_proactive_loading():
    """Test proactive context loading planning."""
    print("Testing ProactiveContextLoader...")

    detector = EntityDetector()
    loader = ProactiveContextLoader()

    prompt = "How to refactor the authenticate_user() function in auth.py?"
    entities = detector.detect_entities(prompt)

    # Plan loading
    plan = loader.plan_context_loading(entities)
    assert len(plan) > 0
    print(f"  ✓ Planned loading for {len(plan)} entities")

    # Check plan structure
    first_plan = list(plan.values())[0]
    assert "entity" in first_plan
    assert "search_queries" in first_plan
    assert "graph_traversals" in first_plan
    print(f"  ✓ Loading plan structure valid")

    # Test formatting
    formatted = loader.format_loading_plan(max_tokens=200)
    if formatted:
        assert "Pre-loaded Context" in formatted or "Loading" in formatted
        print(f"  ✓ Loading plan formatted ({len(formatted)} chars)")


def test_progressive_disclosure():
    """Test progressive disclosure (drill-down)."""
    print("Testing ProgressiveDisclosureManager...")

    mgr = ProgressiveDisclosureManager()

    # Create references
    ref1 = mgr.create_memory_reference(
        memory_id="jwt_impl_001",
        title="JWT Implementation Pattern",
        memory_type="implementation",
        full_content="Detailed JWT implementation with refresh tokens, expiry handling, and error cases...",
    )
    assert "jwt_impl_001" in ref1
    print(f"  ✓ Created memory reference: {ref1}")

    # Create second reference
    ref2 = mgr.create_memory_reference(
        memory_id="auth_tests_002",
        title="Authentication Test Suite",
        memory_type="procedure",
        full_content="Test cases for login, logout, token refresh, error handling...",
    )
    assert "auth_tests_002" in ref2
    print(f"  ✓ Created second reference")

    # Test drill-down (recall)
    recalled = mgr.recall_memory("jwt_impl_001")
    assert recalled is not None
    assert "JWT Implementation" in recalled["title"]
    assert recalled["accessed_count"] == 1
    print(f"  ✓ Drill-down successful, accessed_count: {recalled['accessed_count']}")

    # Test stats
    stats = mgr.get_drill_down_stats()
    assert stats["total_references"] == 2
    assert stats["accessed_memories"] == 1
    assert stats["total_drill_downs"] == 1
    print(f"  ✓ Drill-down stats: {stats['accessed_memories']}/{stats['total_references']} accessed")


def test_cross_session_continuity():
    """Test cross-session continuity."""
    print("Testing CrossSessionContinuity...")

    mgr = CrossSessionContinuity(session_id="test_session_001")

    # Test gap analysis - brief interruption
    now = datetime.utcnow()
    last_session = now - timedelta(minutes=20)
    gap = mgr.analyze_session_gap(now, last_session)
    assert gap["gap_type"] == "brief_interruption"
    print(f"  ✓ Brief interruption detected: {gap['human_readable']}")

    # Test gap analysis - same day return
    last_session2 = now - timedelta(hours=6)
    gap2 = mgr.analyze_session_gap(now, last_session2)
    assert gap2["gap_type"] == "same_day_return"
    print(f"  ✓ Same-day return detected: {gap2['human_readable']}")

    # Test gap analysis - long break
    last_session3 = now - timedelta(days=10)
    gap3 = mgr.analyze_session_gap(now, last_session3)
    assert gap3["gap_type"] == "long_break"
    print(f"  ✓ Long break detected: {gap3['human_readable']}")

    # Create session summary
    summary = mgr.create_session_summary(
        completed_tasks=[
            "Implemented JWT authentication",
            "Added refresh token logic",
            "Fixed token expiry handling",
        ],
        discovered_insights=[
            "Short-lived tokens improve security",
            "Refresh token rotation prevents token compromise",
        ],
        next_steps=[
            "Add rate limiting to token endpoint",
            "Implement token blacklist for logout",
        ],
        accomplishments="Completed core auth system with JWT",
    )
    assert summary["session_id"] == "test_session_001"
    assert len(summary["completed_tasks"]) == 3
    print(f"  ✓ Session summary created: {summary['accomplishments']}")

    # Test resume formatting
    resume_text = mgr.format_session_resume(gap)
    assert "Session Resume" in resume_text
    assert "Completed" in resume_text or "accomplished" in resume_text.lower()
    print(f"  ✓ Resume context formatted ({len(resume_text)} chars)")


def test_advanced_intelligence_integration():
    """Test full advanced intelligence system."""
    print("Testing AdvancedContextIntelligence (Full Integration)...")

    intel = AdvancedContextIntelligence(session_id="test_session_advanced")

    # Analyze complex prompt
    prompt = (
        "I need to refactor the authenticate_user() function in auth.py. "
        "It should use JWT tokens with 15-minute expiry. Also update the users table schema. "
        "What best practices should I follow for OAuth integration?"
    )

    analysis = intel.analyze_prompt_for_intelligence(prompt)
    assert analysis["entity_count"] > 0
    assert analysis["num_to_preload"] > 0
    print(f"  ✓ Analyzed prompt: {analysis['entity_count']} entities, "
          f"{analysis['num_to_preload']} plans")

    # Test advanced context formatting
    formatted = intel.format_advanced_context(prompt, max_tokens=400)
    if formatted:
        print(f"  ✓ Formatted advanced context ({len(formatted)} chars)")

    # Test intelligence stats
    stats = intel.get_intelligence_stats()
    assert "entities_detected" in stats
    assert "proactive_plans" in stats
    print(f"  ✓ Intelligence stats: {stats}")


def test_entity_id_consistency():
    """Test that entity IDs are consistent."""
    print("Testing Entity ID consistency...")

    entity1 = Entity(
        entity_text="authenticate_user",
        entity_type="function",
        confidence=0.9,
        context_before="def",
        context_after="():",
        position=10,
    )

    entity2 = Entity(
        entity_text="authenticate_user",
        entity_type="function",
        confidence=0.85,
        context_before="call",
        context_after="(token)",
        position=50,
    )

    # Same entity text/type should have same ID
    assert entity1.id == entity2.id
    print(f"  ✓ Entity IDs consistent: {entity1.id} == {entity2.id}")

    # Different entity should have different ID
    entity3 = Entity(
        entity_text="login_user",
        entity_type="function",
        confidence=0.9,
        context_before="def",
        context_after="():",
        position=20,
    )

    assert entity1.id != entity3.id
    print(f"  ✓ Different entities have different IDs")


if __name__ == "__main__":
    print("\n=== Phase 4: Advanced Context Intelligence Tests ===\n")

    try:
        test_entity_detection()
        test_proactive_loading()
        test_progressive_disclosure()
        test_cross_session_continuity()
        test_advanced_intelligence_integration()
        test_entity_id_consistency()

        print("\n✅ All Phase 4 tests passed!\n")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
