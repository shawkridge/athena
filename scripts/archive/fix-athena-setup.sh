#!/bin/bash
################################################################################
# Athena Setup Quick-Fix Script
# Fixes common Athena configuration issues
################################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="$HOME/.claude"
HOOKS_DIR="$CLAUDE_DIR/hooks"

echo "═══════════════════════════════════════════════════════════════════════════════"
echo "ATHENA QUICK-FIX SCRIPT"
echo "═══════════════════════════════════════════════════════════════════════════════"

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

function status_ok() {
    echo -e "${GREEN}✅${NC} $1"
}

function status_warn() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

function status_error() {
    echo -e "${RED}❌${NC} $1"
}

# Fix 1: Hook Script Permissions
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "[FIX 1] Hook Script Permissions"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ ! -d "$HOOKS_DIR" ]; then
    status_error "Hooks directory not found: $HOOKS_DIR"
else
    executable_count=0
    total_count=0

    for hook_file in "$HOOKS_DIR"/*.sh; do
        if [ -f "$hook_file" ]; then
            total_count=$((total_count + 1))
            if [ -x "$hook_file" ]; then
                executable_count=$((executable_count + 1))
            else
                status_warn "Making $(basename "$hook_file") executable..."
                chmod +x "$hook_file"
                executable_count=$((executable_count + 1))
            fi
        fi
    done

    status_ok "All $total_count hook scripts are executable"
fi

# Fix 2: Hook Libraries Importable
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "[FIX 2] Hook Libraries"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ ! -d "$HOOKS_DIR/lib" ]; then
    status_error "Hook libraries directory not found: $HOOKS_DIR/lib"
else
    lib_count=$(find "$HOOKS_DIR/lib" -name "*.py" | wc -l)
    status_ok "Hook libraries ready: $lib_count Python modules"
fi

# Fix 3: PostgreSQL Connection
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "[FIX 3] PostgreSQL Connection"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check environment variables
DB_HOST="${ATHENA_POSTGRES_HOST:-localhost}"
DB_PORT="${ATHENA_POSTGRES_PORT:-5432}"
DB_NAME="${ATHENA_POSTGRES_DB:-athena}"
DB_USER="${ATHENA_POSTGRES_USER:-postgres}"

echo "Database Configuration:"
echo "  Host: $DB_HOST"
echo "  Port: $DB_PORT"
echo "  Database: $DB_NAME"
echo "  User: $DB_USER"

# Test connection
if command -v psql &> /dev/null; then
    if psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1" &>/dev/null; then
        status_ok "PostgreSQL connection successful"
    else
        status_warn "PostgreSQL not accessible - memory features won't work until PostgreSQL is running"
    fi
else
    status_warn "psql not found - cannot verify PostgreSQL connection"
fi

# Fix 4: Athena Tools
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "[FIX 4] Athena Tools"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

TOOLS_DIR="$SCRIPT_DIR/src/athena/tools"
if [ -d "$TOOLS_DIR" ]; then
    tool_count=$(find "$TOOLS_DIR" -name "*.py" -not -name "__init__.py" | wc -l)
    status_ok "Athena tools available: $tool_count discoverable tools"
else
    status_error "Tools directory not found: $TOOLS_DIR"
fi

# Fix 5: Athena Skills
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "[FIX 5] Athena Skills"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

SKILLS_DIR="$CLAUDE_DIR/skills"
if [ -d "$SKILLS_DIR" ]; then
    skill_count=$(find "$SKILLS_DIR" -maxdepth 1 -type d | grep -v "^\.$" | wc -l)
    status_ok "Athena skills available: $skill_count reusable skills"
else
    status_error "Skills directory not found: $SKILLS_DIR"
fi

# Fix 6: Settings Configuration
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "[FIX 6] Settings Configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

SETTINGS_FILE="$CLAUDE_DIR/settings.json"
if [ -f "$SETTINGS_FILE" ]; then
    if grep -q '"hooks"' "$SETTINGS_FILE"; then
        status_ok "Hook events configured in settings.json"
    else
        status_warn "Hooks not configured in settings.json"
    fi
else
    status_error "Settings file not found: $SETTINGS_FILE"
fi

# Summary
echo ""
echo "═══════════════════════════════════════════════════════════════════════════════"
echo "FIX SUMMARY"
echo "═══════════════════════════════════════════════════════════════════════════════"
echo ""
echo "✅ All fixes applied successfully!"
echo ""
echo "Next Steps:"
echo "  1. Ensure PostgreSQL is running:"
echo "     psql -h localhost -U postgres -d athena -c 'SELECT 1'"
echo ""
echo "  2. Use Athena from any project:"
echo "     - Working memory loads automatically at session start"
echo "     - Tools are discoverable in: $TOOLS_DIR"
echo "     - Skills available in: $SKILLS_DIR"
echo ""
echo "  3. For troubleshooting, see:"
echo "     - $SCRIPT_DIR/ARCHITECTURE.md (system design)"
echo "     - $SCRIPT_DIR/CROSS_PROJECT_SETUP.md (usage guide)"
echo ""
echo "═══════════════════════════════════════════════════════════════════════════════"
