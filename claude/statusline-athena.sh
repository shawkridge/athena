#!/usr/bin/env bash
#
# Athena Memory System Status Line for Claude Code
#
# This script displays real-time Athena memory system health and statistics.
# It receives JSON context via stdin and outputs a formatted status line.
#
# Performance: Designed for <100ms execution via connection pooling and caching
# Output: Dimmed terminal colors, concise format suitable for status bar

set -euo pipefail

# Read JSON input from stdin
INPUT=$(cat)

# PostgreSQL connection details (with defaults)
PGHOST="${ATHENA_POSTGRES_HOST:-localhost}"
PGPORT="${ATHENA_POSTGRES_PORT:-5432}"
PGDB="${ATHENA_POSTGRES_DB:-athena}"
PGUSER="${ATHENA_POSTGRES_USER:-postgres}"
export PGPASSWORD="${ATHENA_POSTGRES_PASSWORD:-postgres}"

# ANSI color codes (dimmed for status line)
DIM='\033[2m'
GREEN='\033[32m'
YELLOW='\033[33m'
RED='\033[31m'
BLUE='\033[34m'
CYAN='\033[36m'
RESET='\033[0m'

# Helper: Format bytes to human-readable
format_bytes() {
    local bytes=$1
    if [ "$bytes" -lt 1024 ]; then
        echo "${bytes}B"
    elif [ "$bytes" -lt 1048576 ]; then
        echo "$((bytes / 1024))KB"
    elif [ "$bytes" -lt 1073741824 ]; then
        echo "$((bytes / 1048576))MB"
    else
        echo "$((bytes / 1073741824))GB"
    fi
}

# Helper: Check PostgreSQL connection (with timeout)
check_pg_connection() {
    timeout 2 psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDB" -tAc "SELECT 1" 2>/dev/null || echo "0"
}

# Helper: Get database size
get_db_size() {
    psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDB" -tAc \
        "SELECT pg_database_size('$PGDB')" 2>/dev/null || echo "0"
}

# Helper: Get project ID from current working directory
get_project_id() {
    local cwd=$1
    psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDB" -tAc \
        "SELECT id FROM projects WHERE path = '$cwd' LIMIT 1" 2>/dev/null || echo ""
}

# Helper: Get all 8 layer counts for current project
# L1-L5,L7-L8 are per-project; L6 (meta) is global
get_project_layer_counts() {
    local project_id=$1
    psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDB" -tAc \
        "SELECT
            (SELECT COUNT(*) FROM episodic_events WHERE project_id = $project_id) as l1,
            (SELECT COUNT(*) FROM semantic_memories WHERE project_id = $project_id) as l2,
            (SELECT COUNT(*) FROM procedures WHERE project_id = $project_id) as l3,
            (SELECT COUNT(*) FROM prospective_tasks WHERE project_id = $project_id) as l4,
            (SELECT COUNT(*) FROM entities WHERE project_id = $project_id) as l5,
            (SELECT COUNT(*) FROM agent_domain_expertise) as l6,
            (SELECT COUNT(*) FROM consolidation_runs WHERE project_id = $project_id) as l7,
            (SELECT COUNT(*) FROM planning_decisions WHERE project_id = $project_id) as l8" 2>/dev/null || echo "0|0|0|0|0|0|0|0"
}

# Helper: Get working memory for current project (ranked by ACT-R activation)
get_project_working_memory() {
    local project_id=$1
    psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDB" -tAc \
        "SELECT COUNT(*) FROM (
            SELECT id FROM episodic_events
            WHERE project_id = $project_id AND lifecycle_status = 'active'
            ORDER BY
                (-0.5 * LN(GREATEST(EXTRACT(EPOCH FROM (NOW() - last_activation)) / 3600.0, 0.1)))
                + (LN(GREATEST(activation_count, 1)) * 0.1)
                + (COALESCE(consolidation_score, 0) * 1.0)
                + CASE WHEN importance_score > 0.7 THEN 1.5 ELSE 0 END
                + CASE WHEN has_next_step = 1 OR actionability_score > 0.7 THEN 1.0 ELSE 0 END
                + CASE WHEN outcome = 'success' THEN 0.5 ELSE 0 END
            DESC, timestamp DESC
            LIMIT 7
        ) AS wm" 2>/dev/null || echo "0"
}

# Helper: Get active connection count
get_connection_count() {
    psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDB" -tAc \
        "SELECT COUNT(*) FROM pg_stat_activity WHERE datname = '$PGDB' AND state = 'active'" 2>/dev/null || echo "0"
}

# Helper: Get working memory item count (top items by ACT-R activation)
get_working_memory_count() {
    psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDB" -tAc \
        "SELECT COUNT(*) FROM (
            SELECT id FROM episodic_events
            WHERE lifecycle_status = 'active'
            ORDER BY
                (-0.5 * LN(GREATEST(EXTRACT(EPOCH FROM (NOW() - last_activation)) / 3600.0, 0.1)))
                + (LN(GREATEST(activation_count, 1)) * 0.1)
                + (COALESCE(consolidation_score, 0) * 1.0)
                + CASE WHEN importance_score > 0.7 THEN 1.5 ELSE 0 END
                + CASE WHEN has_next_step = 1 OR actionability_score > 0.7 THEN 1.0 ELSE 0 END
                + CASE WHEN outcome = 'success' THEN 0.5 ELSE 0 END
            DESC, timestamp DESC
            LIMIT 7
        ) AS wm" 2>/dev/null || echo "0"
}

# Main status line generation
main() {
    # Check PostgreSQL connection status
    local pg_status=$(check_pg_connection)

    if [ "$pg_status" = "1" ]; then
        # Get current working directory from environment or fallback to pwd
        local cwd="${PWD:-.}"

        # Get project ID for current directory
        local project_id=$(get_project_id "$cwd")

        # If no project found, show global stats
        if [ -z "$project_id" ] || [ "$project_id" = "" ]; then
            printf "${DIM}${RED}●${RESET} ${DIM}Athena${RESET} "
            printf "${DIM}${RED}no project${RESET}"
            return
        fi

        # PostgreSQL is up - gather statistics for current project
        local db_size=$(get_db_size)
        local db_size_fmt=$(format_bytes "$db_size")
        local layer_counts=$(get_project_layer_counts "$project_id")
        local connections=$(get_connection_count)
        local working_mem=$(get_project_working_memory "$project_id")

        # Parse layer counts (pipe-separated)
        IFS='|' read -r l1 l2 l3 l4 l5 l6 l7 l8 <<< "$layer_counts"

        # Determine health color based on metrics
        local health_color="$GREEN"
        if [ "$connections" -gt 8 ]; then
            health_color="$YELLOW"  # Warning: high connection count
        fi
        if [ "$db_size" -gt 1073741824 ]; then
            health_color="$YELLOW"  # Warning: DB > 1GB
        fi

        # Build status line with layer names (current project only)
        # Layers: 1=Episodic 2=Semantic 3=Procedural 4=Prospective 5=Graph 6=Meta(global) 7=Consolidation 8=Planning
        printf "${DIM}${health_color}●${RESET} ${DIM}Athena${RESET} "
        printf "${DIM}${CYAN}${db_size_fmt}${RESET} "
        printf "${DIM}│${RESET} "
        printf "${DIM}epi:${BLUE}${l1}${RESET} "
        printf "${DIM}sem:${BLUE}${l2}${RESET} "
        printf "${DIM}proc:${BLUE}${l3}${RESET} "
        printf "${DIM}prosp:${BLUE}${l4}${RESET} "
        printf "${DIM}graph:${BLUE}${l5}${RESET} "
        printf "${DIM}meta:${BLUE}${l6}${RESET}${DIM}*${RESET} "
        printf "${DIM}cons:${BLUE}${l7}${RESET} "
        printf "${DIM}plan:${BLUE}${l8}${RESET} "
        printf "${DIM}│${RESET} "
        printf "${DIM}wm:${BLUE}${working_mem}${RESET}${DIM}/7${RESET} "
        printf "${DIM}│${RESET} "
        printf "${DIM}${connections}c${RESET}"
    else
        # PostgreSQL is down - show error status
        printf "${DIM}${RED}●${RESET} ${DIM}Athena${RESET} "
        printf "${DIM}${RED}disconnected${RESET}"
    fi
}

# Execute
main
