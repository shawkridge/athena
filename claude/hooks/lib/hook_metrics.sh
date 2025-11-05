#!/bin/bash
#
# Hook Metrics Dashboard - View hook execution statistics
#
# Usage:
#   hook_metrics              # Show all hook stats
#   hook_metrics session-end  # Show specific hook stats
#   hook_metrics --csv        # Export to CSV
#

source ~/.claude/hooks/lib/hook_logger.sh 2>/dev/null || {
  echo "Error: Cannot source hook_logger.sh"
  exit 1
}

# Parse arguments
FILTER_HOOK="$1"
EXPORT_CSV=false

if [ "$1" = "--csv" ]; then
  export_hook_logs_csv "/tmp/hook_logs.csv"
  exit $?
fi

# Display metrics
if [ -z "$FILTER_HOOK" ]; then
  echo ""
  echo "╔════════════════════════════════════════════════════════════════════════════╗"
  echo "║                    HOOK EXECUTION METRICS DASHBOARD                        ║"
  echo "╚════════════════════════════════════════════════════════════════════════════╝"
  echo ""
  all_hook_stats
  echo ""
  echo "📊 Legend:"
  echo "  ✓ = Success  |  ✗ = Failure  |  ⏱ = Timeout  |  ⚠️ = Slow (>200ms)"
  echo ""
  echo "Commands:"
  echo "  hook_metrics [hook-name]   - Show stats for specific hook"
  echo "  hook_metrics --csv         - Export all logs to /tmp/hook_logs.csv"
  echo ""
else
  echo ""
  echo "╔════════════════════════════════════════════════════════════════════════════╗"
  echo "║                    HOOK METRICS: $FILTER_HOOK"
  echo "╚════════════════════════════════════════════════════════════════════════════╝"
  echo ""
  hook_stats "$FILTER_HOOK"
  echo ""
fi
