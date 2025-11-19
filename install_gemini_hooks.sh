#!/bin/bash
#
# This script configures the global Gemini CLI hooks to integrate with the Athena Memory system.
# It uses the same shell scripts as the claude-code environment.
#
# To run this script:
# bash install_gemini_hooks.sh
#

set -e

# --- Configuration ---
# Absolute path to the directory where the Athena hook scripts are located
HOOKS_DIR="/home/user/.work/athena/claude/hooks"

# Path for the Gemini CLI global settings
GEMINI_CONFIG_DIR="/home/user/.gemini"
GEMINI_SETTINGS_FILE="$GEMINI_CONFIG_DIR/settings.json"

# --- Main Logic ---
echo "Creating Gemini CLI global config directory..."
mkdir -p "$GEMINI_CONFIG_DIR"

echo "Writing hooks configuration to $GEMINI_SETTINGS_FILE..."

# Create the JSON configuration for the hooks.
# Note: Hook names like 'SessionStart' and 'SessionEnd' are logical assumptions
# based on the Athena model. They may need to be updated if Gemini CLI uses different names.
cat > "$GEMINI_SETTINGS_FILE" << EOL
{
  "hooks": {
    "SessionStart": {
      "command": "${HOOKS_DIR}/session-start.sh",
      "blocking": true
    },
    "BeforeModel": {
      "command": "${HOOKS_DIR}/user-prompt-submit.sh",
      "blocking": true
    },
    "AfterTool": {
      "command": "${HOOKS_DIR}/post-tool-use.sh",
      "blocking": true
    },
    "SessionEnd": {
      "command": "${HOOKS_DIR}/session-end.sh",
      "blocking": false
    }
  }
}
EOL

echo ""
echo "✅ Global Gemini CLI hooks have been configured successfully!"
echo "The configuration has been saved to $GEMINI_SETTINGS_FILE."
echo "Please restart your Gemini CLI session for the changes to take effect."
