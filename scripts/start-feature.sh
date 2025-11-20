#!/bin/bash
# Start a new feature worktree with automatic setup
# Usage: ./start-feature.sh "feature/name" "optional description"

set -e

FEATURE_NAME="${1:-}"
DESCRIPTION="${2:-}"

if [ -z "$FEATURE_NAME" ]; then
    echo "❌ Usage: start-feature.sh 'feature/name' 'optional description'"
    echo ""
    echo "Examples:"
    echo "  start-feature.sh 'feature/user-auth' 'Implement JWT authentication'"
    echo "  start-feature.sh 'fix/memory-leak' 'Fix connection pool leak'"
    exit 1
fi

# Determine base name from feature name
if [[ $FEATURE_NAME == feature/* ]]; then
    BASE_NAME="${FEATURE_NAME#feature/}"
    BRANCH_TYPE="feature"
elif [[ $FEATURE_NAME == fix/* ]]; then
    BASE_NAME="${FEATURE_NAME#fix/}"
    BRANCH_TYPE="fix"
else
    BASE_NAME="$FEATURE_NAME"
    BRANCH_TYPE="feature"
    FEATURE_NAME="$BRANCH_TYPE/$FEATURE_NAME"
fi

# Worktree path
MAIN_REPO="/home/user/.work/athena"
WORKTREE_PATH="/home/user/.work/athena-$BASE_NAME"

# Color output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}Starting new feature: $FEATURE_NAME${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Step 1: Create worktree
echo -e "${YELLOW}1. Creating git worktree...${NC}"
cd "$MAIN_REPO"
git worktree add "$WORKTREE_PATH" -b "$FEATURE_NAME"
echo -e "${GREEN}   ✓ Worktree created: $WORKTREE_PATH${NC}"
echo ""

# Step 2: Verify worktree
echo -e "${YELLOW}2. Verifying worktree setup...${NC}"
cd "$WORKTREE_PATH"
echo -e "${GREEN}   ✓ Current directory: $(pwd)${NC}"
echo -e "${GREEN}   ✓ Branch: $(git branch --show-current)${NC}"
echo ""

# Step 3: Initialize worktree context
echo -e "${YELLOW}3. Initializing worktree context...${NC}"
echo -e "${GREEN}   ✓ Worktree path: $WORKTREE_PATH${NC}"
echo -e "${GREEN}   ✓ Feature name: $BASE_NAME${NC}"
echo ""

# Step 4: Store feature metadata for Claude Code
echo -e "${YELLOW}4. Setting up feature metadata...${NC}"
cat > .feature.env << EOF
FEATURE_NAME="$BASE_NAME"
FEATURE_BRANCH="$FEATURE_NAME"
FEATURE_TYPE="$BRANCH_TYPE"
WORKTREE_PATH="$WORKTREE_PATH"
CREATED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
DESCRIPTION="$DESCRIPTION"
EOF
echo -e "${GREEN}   ✓ Feature metadata saved${NC}"
echo ""

# Step 5: Ready message
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ Feature worktree ready!${NC}"
echo ""
echo -e "Start working:"
echo -e "  ${YELLOW}cd $WORKTREE_PATH${NC}"
echo -e "  ${YELLOW}claude code${NC}"
echo ""
echo -e "Current location: ${GREEN}$(pwd)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
