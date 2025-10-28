#!/bin/bash
# Installation script for Claude Code Notification Hook System
# Usage: bash install.sh [options]

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARTIFACTS_DIR="$SCRIPT_DIR/artifacts"

# Default settings file (team-wide)
SETTINGS_FILE=".claude/settings.json"
USE_LOCAL=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --local)
            SETTINGS_FILE=".claude/settings.local.json"
            USE_LOCAL=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --local    Install to .claude/settings.local.json instead of settings.json"
            echo "  --help     Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0              # Install to settings.json (team-wide)"
            echo "  $0 --local      # Install to settings.local.json (personal)"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo -e "${BOLD}Claude Code Notification Hook System - Installation${NC}"
echo ""

# Check if we're in a project directory
if [ ! -d ".git" ]; then
    echo -e "${YELLOW}Warning: Not in a git repository. Continuing anyway...${NC}"
fi

# Step 1: Create .claude/hooks directory
echo -e "${BLUE}[1/4]${NC} Creating .claude/hooks directory..."
mkdir -p .claude/hooks
echo -e "${GREEN}✓${NC} Directory created"
echo ""

# Step 2: Copy artifact files
echo -e "${BLUE}[2/4]${NC} Copying hook artifacts..."

if [ ! -f "$ARTIFACTS_DIR/notification-hook.py" ]; then
    echo -e "${RED}✗ Error: notification-hook.py not found at $ARTIFACTS_DIR${NC}"
    exit 1
fi

if [ ! -f "$ARTIFACTS_DIR/view-notifications.sh" ]; then
    echo -e "${RED}✗ Error: view-notifications.sh not found at $ARTIFACTS_DIR${NC}"
    exit 1
fi

cp "$ARTIFACTS_DIR/notification-hook.py" .claude/hooks/
cp "$ARTIFACTS_DIR/view-notifications.sh" .claude/hooks/

# Make scripts executable
chmod +x .claude/hooks/notification-hook.py
chmod +x .claude/hooks/view-notifications.sh

echo -e "${GREEN}✓${NC} notification-hook.py copied"
echo -e "${GREEN}✓${NC} view-notifications.sh copied"
echo -e "${GREEN}✓${NC} Scripts made executable"
echo ""

# Step 3: Configure hooks in settings file
echo -e "${BLUE}[3/4]${NC} Configuring hooks in $SETTINGS_FILE..."

# Create .claude directory if it doesn't exist
mkdir -p .claude

# Check if settings file exists
if [ ! -f "$SETTINGS_FILE" ]; then
    echo -e "${YELLOW}Settings file not found. Creating new file...${NC}"
    cat > "$SETTINGS_FILE" << 'EOF'
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/hooks/notification-hook.py"
          }
        ]
      }
    ]
  }
}
EOF
    echo -e "${GREEN}✓${NC} Created $SETTINGS_FILE with hook configuration"
else
    # Check if hooks already configured
    if grep -q "notification-hook.py" "$SETTINGS_FILE"; then
        echo -e "${YELLOW}⚠${NC}  Hooks already configured in $SETTINGS_FILE"
        echo -e "${YELLOW}⚠${NC}  Skipping hook configuration (already present)"
    else
        echo -e "${YELLOW}⚠${NC}  Settings file exists but hooks not configured"
        echo -e "${YELLOW}⚠${NC}  Please manually add the following to $SETTINGS_FILE:"
        echo ""
        echo -e "${BLUE}\"hooks\": {${NC}"
        echo -e "${BLUE}  \"Stop\": [${NC}"
        echo -e "${BLUE}    {${NC}"
        echo -e "${BLUE}      \"hooks\": [${NC}"
        echo -e "${BLUE}        {${NC}"
        echo -e "${BLUE}          \"type\": \"command\",${NC}"
        echo -e "${BLUE}          \"command\": \"python3 .claude/hooks/notification-hook.py\"${NC}"
        echo -e "${BLUE}        }${NC}"
        echo -e "${BLUE}      ]${NC}"
        echo -e "${BLUE}    }${NC}"
        echo -e "${BLUE}  ]${NC}"
        echo -e "${BLUE}}${NC}"
        echo ""
    fi
fi
echo ""

# Step 4: Validation
echo -e "${BLUE}[4/4]${NC} Validating installation..."

# Check if files exist and are executable
VALIDATION_FAILED=false

if [ ! -x .claude/hooks/notification-hook.py ]; then
    echo -e "${RED}✗${NC} notification-hook.py not executable"
    VALIDATION_FAILED=true
else
    echo -e "${GREEN}✓${NC} notification-hook.py is executable"
fi

if [ ! -x .claude/hooks/view-notifications.sh ]; then
    echo -e "${RED}✗${NC} view-notifications.sh not executable"
    VALIDATION_FAILED=true
else
    echo -e "${GREEN}✓${NC} view-notifications.sh is executable"
fi

if [ ! -f "$SETTINGS_FILE" ]; then
    echo -e "${RED}✗${NC} $SETTINGS_FILE not found"
    VALIDATION_FAILED=true
else
    echo -e "${GREEN}✓${NC} $SETTINGS_FILE exists"
fi

# Test Python availability
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗${NC} python3 not found in PATH"
    VALIDATION_FAILED=true
else
    echo -e "${GREEN}✓${NC} python3 is available"
fi

echo ""

if [ "$VALIDATION_FAILED" = true ]; then
    echo -e "${RED}Installation completed with errors. Please fix the issues above.${NC}"
    exit 1
fi

# Success!
echo -e "${GREEN}${BOLD}✓ Installation completed successfully!${NC}"
echo ""
echo -e "${BOLD}Next Steps:${NC}"
echo ""
echo -e "1. Start a Claude Code session in this directory"
echo -e "2. When Claude finishes and waits for input, a notification will be written"
echo -e "3. View notifications with: ${BLUE}./.claude/hooks/view-notifications.sh${NC}"
echo ""
echo -e "${BOLD}Useful commands:${NC}"
echo -e "  ${BLUE}./.claude/hooks/view-notifications.sh${NC}        # View last 10 notifications"
echo -e "  ${BLUE}./.claude/hooks/view-notifications.sh -f${NC}     # Follow notifications in real-time"
echo -e "  ${BLUE}./.claude/hooks/view-notifications.sh -c${NC}     # Clear all notifications"
echo -e "  ${BLUE}./.claude/hooks/view-notifications.sh --help${NC} # Show all options"
echo ""
echo -e "Notification file: ${BLUE}/tmp/claude-notifications.jsonl${NC}"
echo ""
echo -e "${YELLOW}Note: The hook will start working in your next Claude Code session.${NC}"
echo ""
