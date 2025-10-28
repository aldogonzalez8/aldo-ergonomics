#!/usr/bin/env python3
"""
Claude Code notification hook - writes session status to a notification file

Smart Mode (Optional):
  Set ANTHROPIC_API_KEY environment variable to enable smart LLM-based descriptions.
  Requires: pip install anthropic
  Falls back to simple text parsing if not available.

Slack Integration (Optional):
  Set SLACK_BOT_TOKEN and SLACK_USER_ID environment variables to send DMs.
  No extra dependencies required (uses urllib).
"""
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def debug_log(message: str):
    """Write debug message to log file for troubleshooting"""
    try:
        debug_file = Path('/tmp/claude-notification-debug.log')
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with debug_file.open('a') as f:
            f.write(f"[{timestamp}] {message}\n")
    except:
        pass  # Don't let logging break the hook


def read_last_claude_message(transcript_path: str) -> str:
    """
    Read the last assistant message from the transcript to generate a description.
    Returns a brief summary of what Claude just did.
    """
    try:
        transcript = Path(transcript_path).expanduser()
        if not transcript.exists():
            return "Claude is waiting for your input"

        # Read the last few lines (JSONL format)
        lines = transcript.read_text().strip().split('\n')

        # Find the last assistant message with text content
        for line in reversed(lines[-20:]):  # Check last 20 lines
            try:
                entry = json.loads(line)
                if entry.get('role') == 'assistant':
                    # Look for text content in the message
                    content = entry.get('content', [])
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get('type') == 'text':
                                text = block.get('text', '').strip()
                                # Take first sentence or first 100 chars
                                if text:
                                    first_sentence = text.split('\n')[0].split('.')[0]
                                    return first_sentence[:150] + ('...' if len(first_sentence) > 150 else '')
                    elif isinstance(content, str) and content.strip():
                        first_sentence = content.strip().split('\n')[0].split('.')[0]
                        return first_sentence[:150] + ('...' if len(first_sentence) > 150 else '')
            except json.JSONDecodeError:
                continue

        return "Claude is waiting for your input"

    except Exception as e:
        return f"Claude finished (error reading transcript: {str(e)[:50]})"


def get_smart_description(transcript_path: str, max_chars: int = 1000) -> Optional[str]:
    """
    Use Claude API to generate a smart, concise description of what Claude just did.
    Returns None if API key not available or if request fails.
    """
    debug_log("=== Smart Mode Started ===")
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        debug_log("FAIL: No ANTHROPIC_API_KEY found in environment")
        return None
    debug_log(f"SUCCESS: API key found (starts with {api_key[:10]}...)")

    try:
        # Import anthropic only if API key is available
        import anthropic
        debug_log("SUCCESS: anthropic module imported")

        # Read the last few messages from transcript
        transcript = Path(transcript_path).expanduser()
        debug_log(f"Transcript path: {transcript}")
        if not transcript.exists():
            debug_log("FAIL: Transcript file does not exist")
            return None
        debug_log("SUCCESS: Transcript file exists")

        lines = transcript.read_text().strip().split('\n')
        debug_log(f"SUCCESS: Read {len(lines)} lines from transcript")

        # Get ONLY the last assistant message (immediate action)
        last_assistant_text = None
        for line in reversed(lines[-20:]):  # Search last 20 lines
            try:
                entry = json.loads(line)
                # Claude Code transcript format uses "type" instead of "role"
                role = entry.get('type', '')

                if role == 'assistant':
                    # Content is nested in message.content for Claude Code transcripts
                    content = None
                    if 'message' in entry and isinstance(entry['message'], dict):
                        content = entry['message'].get('content', [])
                    else:
                        content = entry.get('content', [])

                    # Extract text from content
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get('type') == 'text':
                                text = block.get('text', '').strip()
                                if text:
                                    last_assistant_text = text[:800]  # Get more context from this one message
                                    break
                    elif isinstance(content, str):
                        last_assistant_text = content[:800]

                    if last_assistant_text:
                        break  # Found it, stop searching
            except Exception as e:
                debug_log(f"Error parsing transcript line: {str(e)}")
                continue

        if not last_assistant_text:
            debug_log("FAIL: No assistant message found in last 20 lines")
            return None
        debug_log(f"SUCCESS: Found assistant text ({len(last_assistant_text)} chars): {last_assistant_text[:100]}...")

        context = last_assistant_text
        debug_log("Making API call to Claude...")

        # Use Claude API with very short timeout
        client = anthropic.Anthropic(api_key=api_key, timeout=3.0)

        message = client.messages.create(
            model="claude-3-5-haiku-20241022",  # Fast, cheap model
            max_tokens=50,
            temperature=0,
            messages=[{
                "role": "user",
                "content": f"""This is Claude's most recent message to the user. What action did Claude JUST complete in THIS message?

Reply with ONE past-tense sentence (10-15 words max) stating the immediate action.

Good examples:
- "Fixed smart mode prompt to focus on immediate actions"
- "Updated README documentation with new features"
- "Refactored notification hook for better performance"
- "Waiting for user approval to proceed"

Bad examples:
- "I apologize but..." (never apologize)
- "Added X, then Y, then Z" (too much history, focus on THIS message only)
- "The user asked about..." (focus on what Claude did, not user)

Claude's message:
{context}"""
            }]
        )

        # Extract the response
        if message.content and len(message.content) > 0:
            response = message.content[0].text.strip()
            # Remove any quotes or extra formatting
            response = response.strip('"\'')
            debug_log(f"SUCCESS: API returned: {response}")
            return response[:150]

        debug_log("FAIL: API returned empty content")
        return None

    except Exception as e:
        # Silently fail and fall back to simple mode
        debug_log(f"FAIL: Exception in smart mode: {type(e).__name__}: {str(e)}")
        return None


def generate_task_description(hook_data: dict) -> str:
    """
    Generate a human-readable description of what Claude is doing/waiting for.
    Uses smart LLM-based description if ANTHROPIC_API_KEY is available,
    otherwise falls back to simple text parsing.
    """
    event = hook_data.get('hook_event_name', '')

    if event == 'Stop':
        # Try to get a smart description from the transcript
        transcript_path = hook_data.get('transcript_path', '')
        if transcript_path:
            # Try smart mode first (if API key available)
            smart_desc = get_smart_description(transcript_path)
            if smart_desc:
                debug_log(f"Using SMART mode description: {smart_desc}")
                return smart_desc
            # Fall back to simple parsing
            debug_log("Falling back to SIMPLE mode")
            return read_last_claude_message(transcript_path)
        return "Claude is waiting for your input"

    elif event == 'Notification':
        # Notification hook fires when Claude needs approval or is idle
        # Use smart mode to get contextual description
        transcript_path = hook_data.get('transcript_path', '')
        if transcript_path:
            smart_desc = get_smart_description(transcript_path)
            if smart_desc:
                return f"{smart_desc} (needs approval)"
            return read_last_claude_message(transcript_path)
        return "Claude needs your approval"

    elif event == 'PreToolUse':
        tool_name = hook_data.get('tool_name', 'unknown')
        tool_input = hook_data.get('tool_input', {})

        if tool_name == 'Write':
            file_path = tool_input.get('file_path', 'a file')
            return f"Claude wants to write to {file_path}"
        elif tool_name == 'Edit':
            file_path = tool_input.get('file_path', 'a file')
            return f"Claude wants to edit {file_path}"
        elif tool_name == 'Bash':
            command = tool_input.get('command', 'a command')[:50]
            return f"Claude wants to run: {command}"
        else:
            return f"Claude wants to use {tool_name} (needs approval)"

    elif event == 'SessionEnd':
        return "Session ended"

    return f"Claude event: {event}"


def write_notification(notification: dict):
    """
    Append notification to the JSONL file in /tmp.
    """
    notification_file = Path('/tmp/claude-notifications.jsonl')

    # Ensure parent directory exists
    notification_file.parent.mkdir(parents=True, exist_ok=True)

    # Append notification as a single JSON line
    with notification_file.open('a') as f:
        f.write(json.dumps(notification) + '\n')


def send_to_slack_dm(notification: dict) -> bool:
    """
    Send notification to Slack via Bot chat.postMessage API (DM to user).
    Returns True if successful, False otherwise.
    Silently fails if not configured or on error (won't block hook).
    """
    bot_token = os.environ.get('SLACK_BOT_TOKEN')
    user_id = os.environ.get('SLACK_USER_ID')

    if not bot_token or not user_id:
        return False  # Silently skip if not configured

    try:
        # Map event to emoji
        event = notification.get('event', 'Unknown')
        emoji_map = {
            'Stop': '🟡',
            'Notification': '🔔',
            'PreToolUse': '🔵',
            'SessionEnd': '⚫'
        }
        emoji = emoji_map.get(event, '⚪')

        # Format timestamp
        timestamp_str = notification.get('timestamp', '')
        try:
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            time_formatted = dt.strftime('%H:%M:%S')
        except:
            time_formatted = 'Unknown'

        # Extract fields
        path = notification.get('code_session_path', 'Unknown')
        session_id = notification.get('session_id', 'Unknown')
        session_short = session_id[:8] if len(session_id) >= 8 else session_id
        task = notification.get('task', 'No description')

        # Build Slack Block Kit message
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{emoji} *Claude Notification*\n━━━━━━━━━━━━━━━━━━━━━"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"📁 *Path:*\n`{path}`"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"🆔 *Session:*\n`{session_short}`"
                    }
                ]
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"📝 *Task:*\n{task}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"⏰ *Time:*\n{time_formatted}"
                    }
                ]
            }
        ]

        payload = {
            "channel": user_id,  # Send to user DM
            "blocks": blocks,
            "text": f"{emoji} Claude: {task}"  # Fallback for notifications
        }

        # POST to Slack API
        url = "https://slack.com/api/chat.postMessage"
        headers = {
            "Authorization": f"Bearer {bot_token}",
            "Content-Type": "application/json; charset=utf-8"
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers=headers,
            method='POST'
        )

        with urllib.request.urlopen(req, timeout=5) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result.get('ok', False)

    except (urllib.error.HTTPError, urllib.error.URLError, Exception):
        # Silent failure - don't block hook
        return False


def main():
    try:
        # Read hook input from stdin
        hook_data = json.load(sys.stdin)

        # Extract relevant fields
        notification = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'code_session_path': hook_data.get('cwd', ''),
            'session_id': hook_data.get('session_id', ''),
            'task': generate_task_description(hook_data),
            'event': hook_data.get('hook_event_name', ''),
            'transcript_path': hook_data.get('transcript_path', ''),
        }

        # Write to notification file
        write_notification(notification)

        # Send to Slack DM (optional, won't block if fails)
        send_to_slack_dm(notification)

        # Exit successfully (don't block the hook)
        sys.exit(0)

    except Exception as e:
        # Log error but don't block Claude
        error_msg = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'error': f"Hook error: {str(e)}",
            'code_session_path': hook_data.get('cwd', '') if 'hook_data' in locals() else '',
        }
        try:
            write_notification(error_msg)
        except:
            pass

        sys.exit(0)  # Don't block even on error


if __name__ == '__main__':
    main()
