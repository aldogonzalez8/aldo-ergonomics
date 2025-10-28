#!/bin/bash
# View Claude Code notifications in a user-friendly format

NOTIFICATION_FILE="/tmp/claude-notifications.jsonl"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Function to display usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -f, --follow     Follow notifications in real-time (like tail -f)"
    echo "  -n NUM           Show last NUM notifications (default: 10)"
    echo "  -c, --clear      Clear all notifications"
    echo "  -h, --help       Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0               Show last 10 notifications"
    echo "  $0 -n 20         Show last 20 notifications"
    echo "  $0 -f            Follow notifications in real-time"
    echo "  $0 -c            Clear all notifications"
}

# Function to format and display a single notification
format_notification() {
    local line="$1"

    # Parse JSON using python
    python3 -c "
import json
import sys
from datetime import datetime

try:
    data = json.loads('$line')

    # Format timestamp
    timestamp = data.get('timestamp', '')
    if timestamp:
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            timestamp = dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            pass

    # Extract fields
    path = data.get('code_session_path', 'Unknown')
    task = data.get('task', 'No description')
    event = data.get('event', '')
    session_id = data.get('session_id', '')[:8]  # Short ID

    # Color-code by event type
    event_color = {
        'Stop': '${YELLOW}',
        'SessionEnd': '${RED}',
        'PreToolUse': '${BLUE}'
    }.get(event, '${NC}')

    print(f'${BOLD}[{timestamp}]${NC} {event_color}Session {session_id}${NC}')
    print(f'  ${GREEN}Path:${NC} {path}')
    print(f'  ${BLUE}Task:${NC} {task}')
    if event:
        print(f'  ${YELLOW}Event:${NC} {event}')
    print('')

except Exception as e:
    print(f'${RED}Error parsing notification: {e}${NC}', file=sys.stderr)
"
}

# Check if notification file exists
check_file() {
    if [ ! -f "$NOTIFICATION_FILE" ]; then
        echo -e "${YELLOW}No notifications yet. The file will be created when Claude finishes a task.${NC}"
        echo -e "${BLUE}Notification file: ${NOTIFICATION_FILE}${NC}"
        return 1
    fi
    return 0
}

# Main logic
FOLLOW=false
NUM_LINES=10
CLEAR=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--follow)
            FOLLOW=true
            shift
            ;;
        -n)
            NUM_LINES="$2"
            shift 2
            ;;
        -c|--clear)
            CLEAR=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Handle clear command
if [ "$CLEAR" = true ]; then
    if [ -f "$NOTIFICATION_FILE" ]; then
        rm "$NOTIFICATION_FILE"
        echo -e "${GREEN}All notifications cleared.${NC}"
    else
        echo -e "${YELLOW}No notifications to clear.${NC}"
    fi
    exit 0
fi

# Handle follow mode
if [ "$FOLLOW" = true ]; then
    echo -e "${BLUE}Following Claude notifications... (Press Ctrl+C to stop)${NC}"
    echo ""

    # Show existing notifications first
    if check_file; then
        tail -n "$NUM_LINES" "$NOTIFICATION_FILE" | while IFS= read -r line; do
            format_notification "$line"
        done
    fi

    # Then follow new ones
    touch "$NOTIFICATION_FILE"  # Create if doesn't exist
    tail -f "$NOTIFICATION_FILE" | while IFS= read -r line; do
        format_notification "$line"
    done
    exit 0
fi

# Default: Show last N notifications
if check_file; then
    echo -e "${BOLD}Last $NUM_LINES Claude notifications:${NC}"
    echo ""

    tail -n "$NUM_LINES" "$NOTIFICATION_FILE" | while IFS= read -r line; do
        format_notification "$line"
    done
fi
