#!/bin/bash
# Test script for checkpoint system end-to-end

set -e

echo "=========================================="
echo "Testing Checkpoint System"
echo "=========================================="

# Set checkpoint environment variables
export CHECKPOINT_TASK="Implement JWT token refresh"
export CHECKPOINT_FILE="src/auth/token.ts"
export CHECKPOINT_TEST="test_token_refresh"
export CHECKPOINT_NEXT="Add refresh handler in AuthService class"
export CHECKPOINT_STATUS="in_progress"
export CHECKPOINT_TEST_STATUS="failing"
export CHECKPOINT_ERROR="Token refresh handler not implemented"

echo ""
echo "✓ Set checkpoint environment variables:"
echo "  TASK: $CHECKPOINT_TASK"
echo "  FILE: $CHECKPOINT_FILE"
echo "  TEST: $CHECKPOINT_TEST"
echo "  NEXT: $CHECKPOINT_NEXT"

# Test checkpoint manager directly
echo ""
echo "Testing CheckpointManager..."
python3 << 'PYTHON_TEST'
import sys
sys.path.insert(0, '/home/user/.claude/hooks/lib')

from checkpoint_manager import CheckpointManager

# Create manager
manager = CheckpointManager()

# Test saving
print("1. Testing checkpoint save...")
event_id = manager.save_checkpoint(
    project_id=1,
    task_name="Implement JWT token refresh",
    file_path="src/auth/token.ts",
    test_name="test_token_refresh",
    next_action="Add refresh handler in AuthService class",
    status="in_progress",
    test_status="failing",
    error_message="Token refresh handler not implemented"
)

if event_id:
    print(f"  ✓ Checkpoint saved with ID: {event_id}")
else:
    print(f"  ✗ Failed to save checkpoint")
    sys.exit(1)

# Test loading
print("2. Testing checkpoint load...")
checkpoint = manager.load_latest_checkpoint(project_id=1)

if checkpoint:
    print(f"  ✓ Checkpoint loaded:")
    print(f"    - Task: {checkpoint['task_name']}")
    print(f"    - File: {checkpoint['file_path']}")
    print(f"    - Test: {checkpoint['test_name']}")
    print(f"    - Next: {checkpoint['next_action']}")
    print(f"    - Status: {checkpoint['test_status']}")
    if checkpoint.get('error_message'):
        print(f"    - Error: {checkpoint['error_message']}")
else:
    print(f"  ✗ Failed to load checkpoint")
    sys.exit(1)

manager.close()

print("3. Verification: All checkpoint fields present")
required_fields = ['task_name', 'file_path', 'test_name', 'next_action', 'status', 'test_status']
for field in required_fields:
    if field in checkpoint:
        print(f"  ✓ {field}: {checkpoint[field]}")
    else:
        print(f"  ✗ Missing field: {field}")
        sys.exit(1)

print("")
print("✓ All tests passed!")
PYTHON_TEST

echo ""
echo "=========================================="
echo "✓ Checkpoint System Test Complete"
echo "=========================================="
echo ""
echo "Summary:"
echo "  - Checkpoint schema: VALID"
echo "  - Save functionality: WORKING"
echo "  - Load functionality: WORKING"
echo "  - Persistence: CONFIRMED"
echo ""
echo "Next steps when using this system:"
echo "  1. Set CHECKPOINT_* environment variables before session ends"
echo "  2. Session-end hook captures and saves checkpoint"
echo "  3. Session-start hook loads checkpoint and prepends to working memory"
echo "  4. Auto-run test determines current state (passing/failing)"
echo "  5. Continue work with full operational context"
echo ""
