#!/bin/bash
# Git Hook: Pre-Commit Architecture Fitness Check
# Purpose: Run architecture fitness functions before allowing commit
# Usage: Symlink to .git/hooks/pre-commit or run manually
#
# Installation:
#   ln -s $(pwd)/claude/hooks/pre-commit-fitness-check.sh .git/hooks/pre-commit
#   chmod +x .git/hooks/pre-commit
#
# To skip checks temporarily:
#   git commit --no-verify

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SKIP_FITNESS_CHECK="${SKIP_FITNESS_CHECK:-false}"
FITNESS_SEVERITY="${FITNESS_SEVERITY:-error}"  # error, warning, or info

# Functions
log_info() {
    echo -e "${BLUE}[FITNESS-CHECK]${NC} $1" >&2
}

log_success() {
    echo -e "${GREEN}[FITNESS-CHECK]${NC} $1" >&2
}

log_warning() {
    echo -e "${YELLOW}[FITNESS-CHECK]${NC} $1" >&2
}

log_error() {
    echo -e "${RED}[FITNESS-CHECK]${NC} $1" >&2
}

# Check if skip flag is set
if [ "$SKIP_FITNESS_CHECK" = "true" ]; then
    log_warning "Fitness check skipped (SKIP_FITNESS_CHECK=true)"
    exit 0
fi

log_info "Running architecture fitness checks..."
log_info "Severity filter: $FITNESS_SEVERITY"

# Change to project root
cd "$(git rev-parse --show-toplevel)"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    log_error "python3 not found - cannot run fitness checks"
    exit 1
fi

# Check if fitness module exists
if [ ! -f "src/athena/architecture/fitness.py" ]; then
    log_warning "Architecture fitness module not found - skipping checks"
    exit 0
fi

# Run fitness checks
# Only check ERROR severity by default (faster for commits)
# Use --fail-on-critical to block commit on failures
if python3 -m athena.cli.fitness_check \
    --severity "$FITNESS_SEVERITY" \
    --fail-on-critical 2>&1; then

    log_success "✅ All critical architecture fitness checks passed"
    exit 0
else
    EXIT_CODE=$?
    log_error "❌ Architecture fitness checks failed"
    log_error ""
    log_error "To see detailed results, run:"
    log_error "  python3 -m athena.cli.fitness_check --verbose"
    log_error ""
    log_error "To bypass this check temporarily (not recommended):"
    log_error "  git commit --no-verify"
    log_error ""
    log_error "Or set environment variable:"
    log_error "  SKIP_FITNESS_CHECK=true git commit"

    exit $EXIT_CODE
fi
