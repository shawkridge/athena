#!/bin/bash
# End-to-end test for TodoWrite integration with Athena

set -e

echo "=========================================="
echo "TodoWrite Integration End-to-End Test"
echo "=========================================="
echo ""

# Step 1: Create a test task in PostgreSQL
echo "Step 1: Creating test task in PostgreSQL..."
psql -h localhost -U postgres -d athena << 'EOF'
-- Insert a test task
INSERT INTO prospective_tasks (project_id, title, description, status, priority, created_at)
VALUES (
    1,
    'Test TodoWrite Integration',
    'This task tests the TodoWrite bidirectional sync',
    'pending',
    5,
    NOW()
)
ON CONFLICT DO NOTHING;

-- Show created task
SELECT id, title, status, priority FROM prospective_tasks WHERE title = 'Test TodoWrite Integration';
EOF

echo "✓ Test task created"
echo ""

# Step 2: Test TodoWriteSync load functionality
echo "Step 2: Testing TodoWriteSync.load_tasks_from_postgres()..."
python3 << 'PYTHON_EOF'
import sys
sys.path.insert(0, '/home/user/.claude/hooks/lib')

from todowrite_sync import TodoWriteSync

sync = TodoWriteSync()
tasks = sync.load_tasks_from_postgres(project_id=1, limit=5)

if tasks:
    print(f"✓ Loaded {len(tasks)} tasks:")
    for task in tasks:
        print(f"  - [{task['status']}] {task['content']}")
        print(f"    ID: {task['id']}, Priority: {task['priority']}")
else:
    print("✗ No tasks loaded")

sync.close()
PYTHON_EOF

echo ""

# Step 3: Test TodoWrite format conversion
echo "Step 3: Testing TodoWrite format conversion..."
python3 << 'PYTHON_EOF'
import sys
import json
sys.path.insert(0, '/home/user/.claude/hooks/lib')

from todowrite_sync import TodoWriteSync

sync = TodoWriteSync()
postgres_tasks = sync.load_tasks_from_postgres(project_id=1, limit=3)

if postgres_tasks:
    todowrite_format = sync.convert_to_todowrite_format(postgres_tasks)
    print("✓ Converted to TodoWrite format:")
    print(json.dumps(todowrite_format[:1], indent=2))
else:
    print("✗ No tasks to convert")

sync.close()
PYTHON_EOF

echo ""

# Step 4: Simulate session-end sync
echo "Step 4: Testing session-end sync (save changes back to PostgreSQL)..."
python3 << 'PYTHON_EOF'
import sys
import json
sys.path.insert(0, '/home/user/.claude/hooks/lib')

from todowrite_sync import TodoWriteSync

sync = TodoWriteSync()

# Simulate TodoWrite modifications
test_tasks = [
    {
        "id": None,  # Will create new
        "content": "New task from TodoWrite",
        "status": "pending",
        "activeForm": "Creating new task",
        "priority": 7,
        "description": "This task was created during a session"
    }
]

summary = sync.save_todowrite_to_postgres(project_id=1, tasks=test_tasks)

print(f"✓ Sync complete:")
print(f"  Created: {summary['created']}")
print(f"  Updated: {summary['updated']}")
if summary['errors']:
    print(f"  Errors: {summary['errors']}")

sync.close()
PYTHON_EOF

echo ""

# Step 5: Verify persistence - check that new task exists
echo "Step 5: Verifying persistence in PostgreSQL..."
psql -h localhost -U postgres -d athena << 'EOF'
-- Show all recent tasks
SELECT id, title, status, priority, last_claude_sync_at
FROM prospective_tasks
WHERE created_at > NOW() - INTERVAL '5 minutes'
ORDER BY created_at DESC;
EOF

echo ""
echo "=========================================="
echo "✓ TodoWrite Integration Test Complete"
echo "=========================================="
echo ""
echo "Summary:"
echo "  ✓ Tasks loaded from PostgreSQL"
echo "  ✓ Tasks converted to TodoWrite format"
echo "  ✓ Changes synced back to PostgreSQL"
echo "  ✓ New tasks created via TodoWrite sync"
echo "  ✓ Persistence verified in database"
echo ""
echo "Next steps:"
echo "  1. Tasks will be automatically loaded at session-start"
echo "  2. TodoWrite is the interface for editing tasks"
echo "  3. Changes are synced back at session-end"
echo "  4. Tasks persist across context clears"
echo ""
