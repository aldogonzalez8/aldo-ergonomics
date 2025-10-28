# Claude Code Notification Hook System

> Stay informed about your Claude Code sessions across multiple projects and terminals

## Overview

This notification system tracks Claude Code session activity and writes structured notifications to a central file when Claude finishes tasks and waits for your input. Never lose track of which Claude session needs your attention!

## Features

- ✅ **Automatic notifications** - Triggers when Claude stops and waits for input
- 💬 **Slack channel-per-repo routing** - Get real-time notifications in dedicated private Slack channels per repository
- 🔄 **Worktree support** - Automatically routes notifications from git worktrees to their parent repo channel
- 🤖 **Auto-channel creation** - Slack channels are created automatically with you invited
- 🔔 **Smart approval tracking** - Only notifies when Claude actually needs your permission (not for auto-allowed tools)
- 🤖 **AI-powered descriptions** - Optional smart mode uses Claude API for contextual summaries
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

### Notification Hook (Smart Approval Tracking) - **RECOMMENDED**

Get notified **only when Claude actually needs your approval**, not for every auto-allowed tool use.

**Why use Notification instead of PreToolUse?**
- ✅ **PreToolUse** fires for EVERY tool use (including auto-allowed ones like `git status`) - annoying!
- ✅ **Notification** fires ONLY when Claude needs approval - perfect!

#### Enabling Notification Hook

Add to `.claude/settings.json`:

```json
{
  "hooks": {
    "Stop": [...],
    "Notification": [
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

#### Example Notification Events

```
[2025-10-28 15:02:06] Session test-write
  Path: /Users/aldo/dev/sonar
  Task: Updated settings (needs approval)
  Event: Notification

[2025-10-28 15:03:12] Session test-bash
  Path: /Users/aldo/dev/sonar
  Task: Proposed running destructive command (needs approval)
  Event: Notification
```

Perfect for tracking when you actually need to take action!

### Slack Integration (Channel-per-Repo Routing)

Get real-time Claude notifications routed to **dedicated private Slack channels per repository**! This is the **recommended way** to stay informed about Claude sessions, especially when working across multiple projects and git worktrees.

**Why Channel-per-Repo?**
- 📂 **Context segmentation** - Each repo gets its own private channel
- 🔄 **Worktree-friendly** - Notifications from `.worktrees/feature-x` go to the parent repo's channel
- 🔒 **Private channels** - Only you and the bot can see them
- 🤖 **Auto-created** - Channels are created automatically when first notification fires
- 📱 **Clean message format** - Just emoji + smart task description (Slack provides timestamp, channel name indicates repo)
- 🚀 **No manual setup** - Channels created and you're invited automatically

**Channel naming pattern:** `claude_notifications_{user_id}_{repo_name}`
- Example: `#claude_notifications_uc56m1dj6_sonar`
- All worktrees from the same repo route to the same channel

#### Setup (5 minutes)

**1. Create Slack App:**
1. Go to https://api.slack.com/apps
2. Click **"Create New App"** → **"From scratch"**
3. Name: **"Claude Code Notifier"** (or your preference)
4. Select your workspace → **"Create App"**

**2. Add Bot Scopes:**
1. In app settings → **"OAuth & Permissions"** (left sidebar)
2. Scroll to **"Scopes"** → **"Bot Token Scopes"**
3. Click **"Add an OAuth Scope"** and add these scopes:
   - `chat:write` (to send messages)
   - `groups:write` (to create and manage private channels)
   - `users:read` (to get user info)

**3. Install App to Workspace:**
1. In **"OAuth & Permissions"**
2. Click **"Install to Workspace"** (top of page)
3. Click **"Allow"** to authorize
4. **Copy the "Bot User OAuth Token"** (starts with `xoxb-`)
   - Example: `xoxb-YOUR-WORKSPACE-ID-YOUR-APP-ID-YOUR-TOKEN-HERE`
   - Save this, you'll need it!

**4. Get Your User ID:**

Two options:

**Option A - From Slack (Easiest):**
1. In Slack, click your profile picture (top right)
2. Click **"Profile"**
3. Click **"..."** (More button)
4. Click **"Copy member ID"**
5. Your ID looks like: `U0G9QF9C6` (starts with U)

**Option B - Use test script:**
```bash
# From your project directory
cd .claude/hooks
SLACK_BOT_TOKEN=xoxb-your-token python3 test-slack.py
```

**5. Configure in settings.json:**

Add both values to `.claude/settings.json`:

```json
{
  "env": {
    "ANTHROPIC_API_KEY": "sk-ant-...",
    "SLACK_BOT_TOKEN": "xoxb-YOUR-TOKEN-HERE",
    "SLACK_USER_ID": "UC56M1DJ6"
  },
  "hooks": {
    "Stop": [...],
    "Notification": [...]
  }
}
```

**6. Test the integration:**

```bash
# Run the test script (from .claude/hooks directory)
python3 test-slack.py

# Or test with environment variables
SLACK_BOT_TOKEN=xoxb-... SLACK_USER_ID=U... python3 test-slack.py
```

You should see:
- ✅ Bot connected successfully
- ✅ Test message sent
- 📱 Check your Slack for the notification!

**7. Start using Claude!**

The first time Claude sends a notification from a project:
- ✅ Private channel is created automatically (e.g., `#claude_notifications_uc56m1dj6_sonar`)
- ✅ You're invited to the channel automatically
- ✅ Notification is posted to the channel

#### Example Slack Message Format

Simple and clean - just what you need:

```
🟡 Simplified Slack message format to show only smart task description
```

That's it! No redundant metadata:
- ❌ No path (channel name already indicates the repo)
- ❌ No session ID (not needed in channel context)
- ❌ No timestamp (Slack provides this automatically)

Just the emoji indicating event type and the smart AI-generated description of what Claude just did.

#### Features

- ✅ **One channel per repo** - Clean organization
- ✅ **Private channels** - Only you can see them
- ✅ **Auto-created channels** - No manual setup needed
- ✅ **Auto-invitation** - You're invited when channel is created
- ✅ **Worktree support** - Automatically routes to parent repo channel
- ✅ **Event-based emojis** (🟡 Stop, 🔔 Notification, ⚫ SessionEnd)
- ✅ **Minimal message format** - Clean, focused notifications
- ✅ **Silent failure** - Won't block hooks if Slack is down
- ✅ **Dual output** - Works alongside file notifications
- ✅ **No dependencies** - Uses Python standard library

#### Troubleshooting

**"missing_scope" error when creating channels:**
- Make sure you added `groups:write` scope (for private channels)
- Re-install the app after adding scopes
- Note: `channels:manage` is for public channels, `groups:write` is for private channels

**Channel created but I can't see it:**
- Check private channels in Slack (not public channels)
- Ensure you were invited when the channel was created
- Look for channels starting with `claude_notifications_`

**"invalid_auth" error:**
- Check that your bot token is correct
- Make sure it starts with `xoxb-`
- Token may have been regenerated - get a new one from Slack app settings

**"channel_not_found" error:**
- Your `SLACK_USER_ID` is incorrect
- Get it from your Slack profile (see step 4 above)

**Messages not appearing:**
- Check private channels (not DMs)
- Look for channels named `claude_notifications_{your_user_id}_{repo_name}`
- Check Slack notification settings

## Configuration Options

### Change Notification File Location

Edit `notification-hook.py` line 90:
```python
notification_file = Path('/tmp/claude-notifications.jsonl')
# Change to your preferred location
```

### Add More Hook Events

The system supports multiple hooks. For approval tracking, we **recommend** `Notification` (only fires when approval actually needed):

```json
{
  "hooks": {
    "Stop": [...],
    "Notification": [
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

**Note:** You can also use `PreToolUse` instead, but it fires for ALL tool uses (even auto-allowed ones), which can be spammy.

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
- [x] ~~**Approval tracking**~~ - ✅ DONE! Get notified only when Claude needs approval (Notification hook)
- [x] ~~**Slack integration**~~ - ✅ DONE! Send DMs directly to your Slack account
- [ ] **Desktop notifications** - Use OS notifications (macOS/Linux/Windows)
- [ ] **Web dashboard** - Simple HTTP server for viewing across machines
- [ ] **Discord integration** - Post notifications to Discord channels
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

**Version:** 2.4.0
**What's New in v2.4:**
- 📂 **Channel-per-repo routing**: Dedicated private Slack channels for each repository
- 🔄 **Worktree support**: Automatically routes notifications from git worktrees to parent repo channel
- 🤖 **Auto-channel creation**: Channels created automatically with user invitation on first notification
- 📱 **Simplified message format**: Clean emoji + smart description format (removed redundant metadata)
- ⚡ **Better context segmentation**: Keep notifications organized by project

**Previous Updates:**
- v2.3: Notification hook (RECOMMENDED) - only fires when approval actually needed
- v2.2: Python 3.9 compatibility fix for type hints
- v2.1: Slack Bot Integration with real-time DM notifications
- v2.0: Smart Mode (AI descriptions) + PreToolUse Hook (approval tracking)
- v1.0: Initial release with file notifications and viewer

**Last Updated:** 2025-10-28