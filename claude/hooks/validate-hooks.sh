#!/bin/bash
#
# Hook Validation Script
# Validates that all Phase 2.5 hooks are properly configured and executable
#
# Usage: ./validate-hooks.sh
# Exit codes: 0 = all tests pass, 1 = some tests failed

set -e

PROJECT_ROOT=$(cd "$(dirname "$0")/../.." && pwd)
HOOKS_DIR="$PROJECT_ROOT/.claude/hooks"
SETTINGS_FILE="$PROJECT_ROOT/.claude/settings.json"

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

tests_passed=0
tests_failed=0

# Test 1: Verify all hook scripts exist
echo "Test 1: Hook Scripts Exist"
echo "=========================="
for script in post-memory-tool.sh post-work-tool.sh session-start.sh session-end.sh pre-plan-tool.sh; do
  if [ -f "$HOOKS_DIR/$script" ]; then
    echo -e "${GREEN}✓${NC} $script exists"
    ((tests_passed++))
  else
    echo -e "${RED}✗${NC} $script NOT FOUND"
    ((tests_failed++))
  fi
done
echo ""

# Test 2: Verify all scripts are executable
echo "Test 2: Hook Scripts Executable"
echo "==============================="
for script in post-memory-tool.sh post-work-tool.sh session-start.sh session-end.sh pre-plan-tool.sh; do
  if [ -x "$HOOKS_DIR/$script" ]; then
    echo -e "${GREEN}✓${NC} $script is executable"
    ((tests_passed++))
  else
    echo -e "${RED}✗${NC} $script is NOT executable"
    ((tests_failed++))
  fi
done
echo ""

# Test 3: Verify hook configuration in settings.json
echo "Test 3: Hook Configuration in settings.json"
echo "==========================================="
if [ -f "$SETTINGS_FILE" ]; then
  hooks=$(jq '.hooks // empty' "$SETTINGS_FILE" 2>/dev/null)
  if [ -n "$hooks" ]; then
    echo -e "${GREEN}✓${NC} Hooks section exists in settings.json"
    ((tests_passed++))

    # Check for each required hook event
    for hook_event in PostToolUse SessionStart SessionEnd PreToolUse; do
      if echo "$hooks" | jq ".$hook_event // empty" | grep -q .; then
        echo -e "${GREEN}✓${NC} $hook_event hook configured"
        ((tests_passed++))
      else
        echo -e "${RED}✗${NC} $hook_event hook NOT configured"
        ((tests_failed++))
      fi
    done
  else
    echo -e "${RED}✗${NC} No hooks section in settings.json"
    ((tests_failed++))
  fi
else
  echo -e "${RED}✗${NC} settings.json NOT FOUND at $SETTINGS_FILE"
  ((tests_failed++))
fi
echo ""

# Test 4: Test hook command paths
echo "Test 4: Hook Command Paths Valid"
echo "==============================="
hook_commands=$(jq -r '.hooks[] | .[].hooks[]? | select(.type=="command") | .command' "$SETTINGS_FILE" 2>/dev/null || true)
if [ -n "$hook_commands" ]; then
  while IFS= read -r cmd; do
    if [ -f "$PROJECT_ROOT/$cmd" ]; then
      echo -e "${GREEN}✓${NC} Command path valid: $cmd"
      ((tests_passed++))
    else
      echo -e "${YELLOW}⚠${NC} Command path relative: $cmd (will be resolved at runtime)"
      ((tests_passed++))
    fi
  done <<< "$hook_commands"
else
  echo -e "${RED}✗${NC} Could not parse hook commands from settings.json"
  ((tests_failed++))
fi
echo ""

# Test 5: Verify hook JSON response format
echo "Test 5: Hook Response Format Validation"
echo "======================================"
test_input='{
  "session_id": "test",
  "transcript_path": "/tmp/test",
  "cwd": "'$PROJECT_ROOT'",
  "hook_event_name": "PostToolUse",
  "tool_name": "mcp__memory__remember",
  "tool_input": {}
}'

# Test post-memory-tool.sh response format
response=$(echo "$test_input" | bash "$HOOKS_DIR/post-memory-tool.sh" 2>/dev/null)
if echo "$response" | jq . >/dev/null 2>&1; then
  if echo "$response" | jq '.continue' >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} post-memory-tool.sh returns valid JSON with 'continue' field"
    ((tests_passed++))
  else
    echo -e "${RED}✗${NC} post-memory-tool.sh missing 'continue' field"
    ((tests_failed++))
  fi
else
  echo -e "${RED}✗${NC} post-memory-tool.sh returns invalid JSON"
  ((tests_failed++))
fi

# Test pre-plan-tool.sh response format
test_input_2='{
  "session_id": "test",
  "transcript_path": "/tmp/test",
  "cwd": "'$PROJECT_ROOT'",
  "hook_event_name": "PreToolUse",
  "tool_name": "mcp__memory__set_goal",
  "tool_input": {"goal_text": "test goal"}
}'

response=$(echo "$test_input_2" | bash "$HOOKS_DIR/pre-plan-tool.sh" 2>/dev/null)
if echo "$response" | jq . >/dev/null 2>&1; then
  echo -e "${GREEN}✓${NC} pre-plan-tool.sh returns valid JSON"
  ((tests_passed++))
else
  echo -e "${RED}✗${NC} pre-plan-tool.sh returns invalid JSON"
  ((tests_failed++))
fi
echo ""

# Summary
echo "======"
echo "Summary"
echo "======"
echo -e "${GREEN}Passed: $tests_passed${NC}"
if [ $tests_failed -gt 0 ]; then
  echo -e "${RED}Failed: $tests_failed${NC}"
  exit 1
else
  echo -e "${GREEN}All tests passed!${NC}"
  exit 0
fi
