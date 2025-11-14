#!/usr/bin/env python3
"""Unit tests for response capture and conversation threading."""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from response_capture import (
    ResponseTurn,
    ToolExecution,
    ResponseCapture,
    ConversationThreader,
    ConversationMemoryBridge,
)


def test_response_turn():
    """Test ResponseTurn data structure."""
    print("Testing ResponseTurn...")

    response_text = "Here's how to implement JWT..."
    turn = ResponseTurn(
        turn_id="turn_001",
        user_question_id="q_001",
        response_content=response_text,
        response_length=len(response_text),
        tools_used=["Read", "Write"],
        tool_results=[],
        timestamp=datetime.utcnow().isoformat(),
        response_time_ms=1234.5,
    )

    assert turn.turn_id == "turn_001"
    assert len(turn.response_content) == turn.response_length
    assert len(turn.tools_used) == 2
    print(f"  ✓ ResponseTurn created with {len(turn.tools_used)} tools")

    # Test conversion to episodic event
    event = turn.to_episodic_event()
    assert event["event_type"] == "claude_response"
    assert event["metadata"]["turn_id"] == "turn_001"
    print(f"  ✓ Converted to episodic event")


def test_tool_execution():
    """Test ToolExecution tracking."""
    print("Testing ToolExecution...")

    execution = ToolExecution(
        tool_name="Read",
        tool_input={"file_path": "/path/to/file.py"},
        tool_output="File contents...",
        execution_time_ms=245.3,
        success=True,
    )

    assert execution.tool_name == "Read"
    assert execution.success == True
    assert execution.execution_time_ms == 245.3
    print(f"  ✓ Tool execution: {execution.tool_name} in {execution.execution_time_ms}ms")

    # Test failed execution
    failed = ToolExecution(
        tool_name="Write",
        tool_input={"file_path": "/path/to/file.py"},
        tool_output="Permission denied",
        execution_time_ms=50.0,
        success=False,
        error_message="Permission denied",
    )

    assert not failed.success
    assert failed.error_message == "Permission denied"
    print(f"  ✓ Failed execution tracked: {failed.error_message}")


def test_response_capture():
    """Test response capture flow."""
    print("Testing ResponseCapture...")

    capture = ResponseCapture()

    # Start turn
    turn_id = capture.start_turn("q_001")
    assert turn_id is not None
    print(f"  ✓ Started turn: {turn_id}")

    # Record response
    capture.record_response("Implementing JWT with short-lived tokens...")
    capture.record_tool_use("Read")
    capture.record_tool_use("Write")

    # Record tool execution
    capture.record_tool_execution(
        tool_name="Read",
        tool_input={"file_path": "auth.py"},
        tool_output="Current auth implementation",
        execution_time_ms=123.4,
        success=True,
    )

    # End turn
    turn = capture.end_turn()
    assert turn is not None
    assert len(turn.tools_used) == 2
    assert len(turn.tool_results) == 1
    print(f"  ✓ Captured turn with {len(turn.tools_used)} tools, "
          f"{len(turn.tool_results)} results")

    # Test summary
    summary = capture.get_turn_summary(turn)
    assert "2 tools" in summary
    print(f"  ✓ Summary: {summary[:60]}...")


def test_conversation_threader():
    """Test conversation threading."""
    print("Testing ConversationThreader...")

    threader = ConversationThreader()

    # Start thread
    thread_id = threader.start_thread(
        user_question_id="q_001",
        user_question="How do I implement JWT authentication?"
    )
    assert thread_id == "q_001"
    print(f"  ✓ Started thread: {thread_id}")

    # Create a turn to add
    turn = ResponseTurn(
        turn_id="turn_001",
        user_question_id="q_001",
        response_content="Use short-lived tokens with refresh tokens...",
        response_length=50,
        tools_used=["Read", "Write"],
        tool_results=[
            {
                "tool_name": "Read",
                "success": True,
                "tool_output": "Current implementation",
                "execution_time_ms": 100,
            }
        ],
        timestamp=datetime.utcnow().isoformat(),
    )

    # Add response
    threader.add_response_to_thread(turn)
    assert len(threader.current_thread["response_turns"]) == 1
    print(f"  ✓ Added response turn to thread")

    # Set outcome
    threader.set_thread_outcome(
        outcome="JWT authentication implemented",
        completed=True,
        result_summary="Added JWT with 15min expiry + refresh tokens"
    )

    assert threader.current_thread["completed"] == True
    assert "JWT" in threader.current_thread["outcome"]
    print(f"  ✓ Thread completed: {threader.current_thread['outcome']}")

    # Test resume format
    resume = threader.get_thread_for_resume("q_001")
    assert resume is not None
    assert "JWT" in resume["question"]
    assert len(resume["tools_used"]) > 0
    print(f"  ✓ Resume format: {resume['question'][:50]}...")

    # Test recent threads
    recent = threader.get_recent_threads(limit=5)
    assert len(recent) == 1
    print(f"  ✓ Retrieved {len(recent)} recent thread(s)")


def test_conversation_memory_bridge():
    """Test full conversation bridge."""
    print("Testing ConversationMemoryBridge...")

    bridge = ConversationMemoryBridge()

    # Process a complete turn
    thread = bridge.process_turn(
        user_question_id="q_001",
        user_question="How do I handle JWT token expiry?",
        response_text="Implement refresh token rotation with sliding window expiry...",
        tools_used=["Read", "Write", "Bash"],
        tool_results=[
            {
                "tool_name": "Read",
                "input": {"file_path": "auth.py"},
                "output": "Current implementation",
                "execution_time_ms": 145.2,
                "success": True,
            },
            {
                "tool_name": "Write",
                "input": {"file_path": "auth_test.py"},
                "output": "Test file written",
                "execution_time_ms": 234.5,
                "success": True,
            },
            {
                "tool_name": "Bash",
                "input": {"command": "pytest tests/auth/test_jwt.py"},
                "output": "All tests passed",
                "execution_time_ms": 1500.0,
                "success": True,
            },
        ],
        response_time_ms=2456.3,
    )

    assert "q_001" in thread.get("thread_id", "")
    assert len(thread.get("response_turns", [])) > 0
    print(f"  ✓ Processed turn with {len(thread.get('response_turns', []))} response(s)")

    # Format for resume
    resume = bridge.format_for_resume(max_threads=1)
    assert "Recent Work" in resume
    assert "JWT" in resume or "token" in resume.lower()
    print(f"  ✓ Formatted for resume ({len(resume)} chars)")

    # Get memory events
    events = bridge.get_memory_events(bridge.threader.threads)
    # Note: Will be empty until outcome is set
    print(f"  ✓ Generated {len(events)} memory events")

    # Set outcome and try again
    bridge.threader.set_thread_outcome(
        outcome="JWT expiry handling implemented",
        completed=True,
        result_summary="Added refresh token rotation with sliding window"
    )

    events = bridge.get_memory_events(bridge.threader.threads)
    assert len(events) > 0
    assert "JWT" in events[0]["content"]
    print(f"  ✓ Generated {len(events)} memory event(s) after completion")


def test_multiple_turns_same_thread():
    """Test multiple turns in same conversation thread."""
    print("Testing multiple turns in conversation...")

    bridge = ConversationMemoryBridge()

    # First turn: Ask about JWT
    bridge.process_turn(
        user_question_id="q_001",
        user_question="How do I implement JWT?",
        response_text="Use short-lived tokens...",
        tools_used=["Read"],
        tool_results=[
            {
                "tool_name": "Read",
                "input": {"file_path": "docs/jwt.md"},
                "output": "JWT documentation",
                "execution_time_ms": 100.0,
                "success": True,
            }
        ],
    )

    first_thread_id = bridge.threader.current_thread["thread_id"]

    # Simulate second follow-up turn in same thread
    capture = bridge.capture
    turn_id = capture.start_turn("q_001")  # Same question ID
    capture.record_response("Also consider token rotation...")
    capture.record_tool_use("Write")
    turn = capture.end_turn()

    bridge.threader.add_response_to_thread(turn)

    # Verify we have 2 response turns in same thread
    assert len(bridge.threader.current_thread["response_turns"]) == 2
    print(f"  ✓ Thread has {len(bridge.threader.current_thread['response_turns'])} response turns")


def test_edge_cases():
    """Test edge cases and error handling."""
    print("Testing edge cases...")

    capture = ResponseCapture()

    # Try to record response without starting turn
    capture.record_response("This should not crash")
    print(f"  ✓ Gracefully handled response without active turn")

    # Empty thread list
    threader = ConversationThreader()
    recent = threader.get_recent_threads()
    assert recent == []
    print(f"  ✓ Empty thread list returns empty list")

    # Non-existent thread
    resume = threader.get_thread_for_resume("nonexistent")
    assert resume is None
    print(f"  ✓ Non-existent thread returns None")


if __name__ == "__main__":
    print("\n=== Response Capture and Conversation Threading Tests ===\n")

    try:
        test_response_turn()
        test_tool_execution()
        test_response_capture()
        test_conversation_threader()
        test_conversation_memory_bridge()
        test_multiple_turns_same_thread()
        test_edge_cases()

        print("\n✅ All response capture tests passed!\n")
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
