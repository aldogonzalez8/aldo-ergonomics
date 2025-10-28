# Claude Code Notification Hook System

> Stay informed about your Claude Code sessions across multiple projects and terminals

## Overview

This notification system tracks Claude Code session activity and writes structured notifications to a central file when Claude finishes tasks and waits for your input. Never lose track of which Claude session needs your attention!

## Features

- ✅ **Automatic notifications** - Triggers when Claude stops and waits for input
- 🔔 **PreToolUse tracking** - Get notified when Claude needs approval for file operations (NEW!)
- 🤖 **AI-powered descriptions** - Optional smart mode uses Claude API for contextual summaries (NEW!)
- 📝 **Smart fallback** - Extracts Claude's last message when smart mode is disabled
- 🎨 **Pretty viewer** - Color-coded terminal UI for easy reading
- 📊 **Structured format** - JSONL format for easy parsing and processing
- 🔄 **Real-time monitoring** - Follow mode to watch notifications as they arrive
- 🚀 **Zero configuration** - Works out of the box after installation

## What It Captures

Each notification includes:
- **Timestamp** - When Claude stopped
- **Session ID** - Unique identifier for the Claude session
- **Project path** - Which codebase Claude is working on
- **Task description** - What Claude just did or is waiting for
- **Event type** - Hook event (Stop, PreToolUse, etc.)
- **Transcript path** - Full conversation location

## Quick Start

### Option 1: Automated Installation (Recommended)

From your project directory:

```bash
# Clone or copy this repository
cd /path/to/your/project
bash /path/to/aldo-ergonomics/claude_hooks/install.sh
```

The script will:
- ✅ Create `.claude/hooks/` directory
- ✅ Copy notification hook scripts
- ✅ Add hook configuration to `.claude/settings.json`
- ✅ Make scripts executable

### Option 2: Manual Installation

1. **Copy the artifacts:**
   ```bash
   mkdir -p .claude/hooks
   cp artifacts/notification-hook.py .claude/hooks/
   cp artifacts/view-notifications.sh .claude/hooks/
   chmod +x .claude/hooks/*.py .claude/hooks/*.sh
   ```

2. **Add to `.claude/settings.json`:**
   ```json
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
   ```

3. **Done!** Start a Claude Code session and the hook will fire automatically.

## Usage

### View Recent Notifications

```bash
./.claude/hooks/view-notifications.sh          # Last 10 notifications
./.claude/hooks/view-notifications.sh -n 20    # Last 20 notifications
```

**Example output:**
```
[2025-10-28 14:36:48] Session b510b600
  Path: /Users/aldo/dev/my-project
  Task: Created notification hook Python script
  Event: Stop
```

### Follow Notifications in Real-Time

```bash
./.claude/hooks/view-notifications.sh -f
```

Great for monitoring multiple Claude sessions across different terminals!

### Clear All Notifications

```bash
./.claude/hooks/view-notifications.sh -c
```

### Direct File Access

The notification file is stored at `/tmp/claude-notifications.jsonl` (JSONL format):

```bash
# View raw notifications
cat /tmp/claude-notifications.jsonl

# Follow raw notifications
tail -f /tmp/claude-notifications.jsonl

# Parse with jq
cat /tmp/claude-notifications.jsonl | jq '.task'
```

## Example Notification JSON

```json
{
  "timestamp": "2025-10-28T14:36:48.790551+00:00",
  "code_session_path": "/Users/aldo/dev/sonar",
  "session_id": "b510b600-e03c-4c95-925e-f25c6a12e438",
  "task": "Created notification hook Python script",
  "event": "Stop",
  "transcript_path": "/Users/aldo/.claude/projects/.../b510b600.jsonl"
}
```

## Use Cases

### 1. **Multiple Project Context Switching**
Working on multiple projects? Get notified when each Claude session finishes so you know which one needs your attention.

### 2. **Long-Running Tasks**
Started a Claude task and switched to another terminal? Get notified when it's done.

### 3. **Session History**
Review what Claude was working on in different sessions throughout the day.

### 4. **Integration with Other Tools**
Parse the JSONL file to:
- Send desktop notifications (macOS `osascript`, Linux `notify-send`)
- Post to Slack/Discord
- Create a web dashboard
- Trigger other automation

## Architecture

```
Claude Code Session
       ↓
   Stop Hook Fires
       ↓
notification-hook.py
  - Reads transcript
  - Extracts last message
  - Generates description
       ↓
/tmp/claude-notifications.jsonl
       ↓
view-notifications.sh
  - Pretty-prints notifications
  - Supports follow mode
```

## Advanced Features

### Smart Mode (AI-Powered Descriptions)

Smart mode uses the Claude API to generate intelligent, contextual task summaries instead of simple text extraction.

**Example comparison:**
- **Simple mode:** "Claude is waiting for your input"
- **Smart mode:** "Updated notification hook with PreToolUse tracking and smart descriptions"

#### Enabling Smart Mode

1. **Install the Anthropic package:**
   ```bash
   pip install anthropic
   ```

2. **Set your API key in `.claude/settings.json`:**
   ```json
   {
     "env": {
       "ANTHROPIC_API_KEY": "sk-ant-your-key-here"
     }
   }
   ```

   Or add to your shell profile (~/.zshrc or ~/.bashrc):
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-your-key-here"
   ```

3. **Restart Claude Code** for the environment variable to take effect.

#### How It Works

- Uses `claude-3-5-haiku-20241022` (fast, cheap model)
- 3-second timeout to avoid blocking hooks
- Automatic fallback to simple mode if API unavailable or fails
- Costs ~$0.0001 per notification (very affordable!)

### PreToolUse Hook (Approval Tracking)

Track when Claude needs your approval to write/edit files or run commands.

#### Enabling PreToolUse

Add to `.claude/settings.json`:

```json
{
  "hooks": {
    "Stop": [...],
    "PreToolUse": [
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
```

#### Example PreToolUse Notifications

```
[2025-10-28 15:02:06] Session test-write
  Path: /Users/aldo/dev/sonar
  Task: Claude wants to write to /test/newfile.py
  Event: PreToolUse

[2025-10-28 15:02:06] Session test-bash
  Path: /Users/aldo/dev/sonar
  Task: Claude wants to run: npm install && npm run build
  Event: PreToolUse
```

Perfect for tracking what Claude wants to do before you approve it!

## Configuration Options

### Change Notification File Location

Edit `notification-hook.py` line 90:
```python
notification_file = Path('/tmp/claude-notifications.jsonl')
# Change to your preferred location
```

### Add More Hook Events

The system currently tracks the `Stop` event. To track other events (like `PreToolUse` for approval requests), add to `.claude/settings.json`:

```json
{
  "hooks": {
    "Stop": [...],
    "PreToolUse": [
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
```

## Troubleshooting

### Hook Not Firing

1. Check that hooks are installed:
   ```bash
   ls -la .claude/hooks/
   ```

2. Verify settings file:
   ```bash
   cat .claude/settings.json | grep -A 10 "hooks"
   ```

3. Test the hook manually:
   ```bash
   echo '{"session_id": "test", "cwd": ".", "hook_event_name": "Stop"}' | \
     python3 .claude/hooks/notification-hook.py
   ```

### Notification File Not Created

- Ensure `/tmp/` is writable
- Check for Python errors: `python3 .claude/hooks/notification-hook.py` (should wait for stdin)

### Viewer Script Not Working

- Ensure Python 3 is installed: `python3 --version`
- Make script executable: `chmod +x .claude/hooks/view-notifications.sh`

## Next Steps / Future Enhancements

- [x] ~~**Smart summaries**~~ - ✅ DONE! Use LLM to generate better task descriptions
- [x] ~~**PreToolUse tracking**~~ - ✅ DONE! Get notified when Claude needs approval
- [ ] **Desktop notifications** - Use OS notifications (macOS/Linux/Windows)
- [ ] **Web dashboard** - Simple HTTP server for viewing across machines
- [ ] **Slack/Discord integration** - Post notifications to team channels
- [ ] **Session analytics** - Track Claude usage patterns and metrics
- [ ] **Filtering** - Filter by project, time range, or event type
- [ ] **Export options** - Export to CSV, Markdown, or other formats

## Contributing

Have an idea to improve this tool? Suggestions welcome!

## License

MIT License - Feel free to use and modify

## Credits

Created by Aldo González for improving Claude Code ergonomics and session management.

---

**Version:** 2.0.0
**What's New in v2.0:**
- 🤖 Smart Mode: AI-powered descriptions using Claude API
- 🔔 PreToolUse Hook: Track approval requests for file operations

**Last Updated:** 2025-10-28