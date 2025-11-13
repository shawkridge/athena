#!/bin/bash

################################################################################
# Setup Athena Nightly Dream Cron Job
#
# This script safely installs the nightly dream consolidation cron job.
# Run as root or with sudo.
#
# Usage:
#   sudo bash setup_cron_job.sh
#   sudo bash setup_cron_job.sh --uninstall
#   sudo bash setup_cron_job.sh --time "0 2"  # Custom time (2 AM)
################################################################################

set -e

# Configuration
ATHENA_HOME="${ATHENA_HOME:-/home/user/.work/athena}"
DREAM_SCRIPT="$ATHENA_HOME/scripts/run_athena_dreams.sh"
CRON_HOUR="2"  # Default: 2 AM
CRON_MINUTE="0"
CRON_JOB_NAME="athena-dreams"
LOG_DIR="/var/log"
LOG_FILE="$LOG_DIR/athena-dreams.log"

################################################################################
# Utility Functions
################################################################################

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

error() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $*" >&2
    exit 1
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        error "This script must be run as root. Use: sudo bash $0"
    fi
}

verify_script() {
    if [ ! -f "$DREAM_SCRIPT" ]; then
        error "Dream script not found: $DREAM_SCRIPT"
    fi

    if [ ! -x "$DREAM_SCRIPT" ]; then
        log "Making dream script executable..."
        chmod +x "$DREAM_SCRIPT"
    fi

    log "✓ Dream script verified: $DREAM_SCRIPT"
}

setup_log_directory() {
    if [ ! -d "$LOG_DIR" ]; then
        mkdir -p "$LOG_DIR"
    fi

    # Create log file if it doesn't exist
    if [ ! -f "$LOG_FILE" ]; then
        touch "$LOG_FILE"
    fi

    # Make world readable
    chmod 644 "$LOG_FILE"

    log "✓ Log directory ready: $LOG_FILE"
}

setup_log_rotation() {
    # Create logrotate config
    LOGROTATE_CONFIG="/etc/logrotate.d/athena-dreams"

    log "Setting up log rotation..."

    cat > "$LOGROTATE_CONFIG" << 'EOF'
/var/log/athena-dreams.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 root root
    sharedscripts
}
EOF

    log "✓ Log rotation configured: $LOGROTATE_CONFIG"
}

install_cron() {
    log "Installing cron job..."

    # Create crontab entry
    CRON_ENTRY="$CRON_MINUTE $CRON_HOUR * * * ATHENA_HOME=$ATHENA_HOME ATHENA_LOG_FILE=$LOG_FILE $DREAM_SCRIPT"

    # Check if job already exists
    if crontab -l 2>/dev/null | grep -q "$CRON_JOB_NAME"; then
        log "Cron job already exists, updating..."
        # Remove old entry
        (crontab -l 2>/dev/null | grep -v "$CRON_JOB_NAME" || true; echo "$CRON_ENTRY") | crontab -
    else
        log "Adding new cron job..."
        # Add to crontab
        (crontab -l 2>/dev/null || echo ""; echo "$CRON_ENTRY") | crontab -
    fi

    log "✓ Cron job installed"
    log "  Schedule: $CRON_HOUR:$CRON_MINUTE daily"
    log "  Command: $DREAM_SCRIPT"
}

verify_cron() {
    log ""
    log "Verifying cron installation..."

    if crontab -l 2>/dev/null | grep -q "$DREAM_SCRIPT"; then
        log "✓ Cron job is installed"
        log ""
        log "Current cron entry:"
        crontab -l 2>/dev/null | grep "$DREAM_SCRIPT"
    else
        error "Cron job installation failed"
    fi
}

uninstall_cron() {
    log "Uninstalling cron job..."

    if crontab -l 2>/dev/null | grep -q "$DREAM_SCRIPT"; then
        (crontab -l 2>/dev/null | grep -v "$DREAM_SCRIPT" || true) | crontab -
        log "✓ Cron job removed"
    else
        log "Cron job not found (already removed?)"
    fi
}

parse_arguments() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --uninstall)
                UNINSTALL=1
                shift
                ;;
            --time)
                shift
                if [ -z "$1" ]; then
                    error "--time requires HH MM argument"
                fi
                CRON_HOUR="$1"
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                ;;
        esac
    done
}

show_help() {
    cat << EOF
Setup Athena Nightly Dream Cron Job

Usage:
  sudo bash $0 [OPTIONS]

Options:
  --time HH MM       Set cron job time (default: 02 00 for 2:00 AM)
  --uninstall        Remove the cron job
  --help            Show this help message

Examples:
  # Install at 2 AM (default)
  sudo bash $0

  # Install at 3 AM
  sudo bash $0 --time 3 0

  # Uninstall
  sudo bash $0 --uninstall

EOF
}

################################################################################
# Main Execution
################################################################################

log "=============================================="
log "Athena Cron Job Setup"
log "=============================================="

# Check arguments
UNINSTALL=0
parse_arguments "$@"

# Check if running as root
check_root

if [ "$UNINSTALL" = "1" ]; then
    log "Uninstall mode"
    uninstall_cron
    log ""
    log "✓ Cron job uninstalled"
    exit 0
fi

# Install mode
log "Install mode"
log "ATHENA_HOME: $ATHENA_HOME"
log "Schedule: $CRON_HOUR:$CRON_MINUTE daily"
log ""

# Step 1: Verify script
verify_script

# Step 2: Setup logging
setup_log_directory
setup_log_rotation

# Step 3: Install cron
install_cron

# Step 4: Verify
verify_cron

log ""
log "=============================================="
log "Setup Complete!"
log "=============================================="
log ""
log "Next steps:"
log "1. Monitor logs: tail -f $LOG_FILE"
log "2. Check cron status: crontab -l"
log "3. Claude will evaluate dreams starting next cycle"
log ""
log "To uninstall: sudo bash $0 --uninstall"
log ""

exit 0
