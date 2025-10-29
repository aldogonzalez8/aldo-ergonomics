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
import re


# Configuration constants for hybrid smart mode
SHORT_MESSAGE_THRESHOLD = 500  # Use full text if message <= this many chars
SMART_SUMMARY_TARGET = 300     # Target length for AI-condensed messages
MAX_SLACK_LENGTH = 1000        # Absolute maximum before hard truncation


def get_repo_name(cwd: str) -> str:
    """
    Extract repository name from cwd path, handling worktrees.

    Examples:
        /Users/aldo/dev/sonar → sonar
        /Users/aldo/dev/sonar/.worktrees/feature-x → sonar
        /Users/aldo → aldo
    """
    path = Path(cwd)

    # Check if in worktree (.worktrees/branch-name)
    if '.worktrees' in path.parts:
        # Find the index of .worktrees and go up to parent
        idx = path.parts.index('.worktrees')
        repo_path = Path(*path.parts[:idx])
        return repo_path.name
    else:
        # Regular repo - return directory name
        return path.name


def sanitize_channel_name(name: str) -> str:
    """
    Sanitize channel name for Slack.
    - Convert to lowercase
    - Replace spaces, underscores, and special chars with hyphens
    - Remove consecutive hyphens

    Examples:
        My_Repo → my-repo
        Sonar DEV → sonar-dev
    """
    # Convert to lowercase
    name = name.lower()
    # Replace underscores and spaces with hyphens
    name = re.sub(r'[_\s]+', '-', name)
    # Remove special characters (keep alphanumeric and hyphens)
    name = re.sub(r'[^a-z0-9-]', '', name)
    # Remove consecutive hyphens
    name = re.sub(r'-+', '-', name)
    # Strip leading/trailing hyphens
    name = name.strip('-')
    return name


def get_slack_channel(cwd: str) -> str:
    """
    Build Slack channel name: claude_notifications_{user_id}_{repo_name}

    Examples:
        /Users/aldo/dev/sonar → claude_notifications_uc56m1dj6_sonar
        /Users/aldo/dev/sonar/.worktrees/feature-x → claude_notifications_uc56m1dj6_sonar
    """
    user_id = os.environ.get('SLACK_USER_ID', '').lower()
    repo_name = sanitize_channel_name(get_repo_name(cwd))
    return f"claude_notifications_{user_id}_{repo_name}"


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
    Read the last assistant message from the transcript.
    Returns the full message text (up to 2000 chars for parsing).
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
                # Claude Code transcript format uses "type" instead of "role"
                role = entry.get('type', '') or entry.get('role', '')

                if role == 'assistant':
                    # Look for text content in the message
                    # Content may be nested in message.content for Claude Code transcripts
                    content = None
                    if 'message' in entry and isinstance(entry['message'], dict):
                        content = entry['message'].get('content', [])
                    else:
                        content = entry.get('content', [])

                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get('type') == 'text':
                                text = block.get('text', '').strip()
                                # Return full message text (with reasonable limit)
                                if text:
                                    return text[:2000]
                    elif isinstance(content, str) and content.strip():
                        return content.strip()[:2000]
            except json.JSONDecodeError:
                continue

        return "Claude is waiting for your input"

    except Exception as e:
        return f"Claude finished (error reading transcript: {str(e)[:50]})"


def get_smart_description(transcript_path: str, target_chars: int = 300) -> Optional[str]:
    """
    Use Claude API to condense long messages to target length.
    Returns None if API key not available or if request fails.

    Args:
        transcript_path: Path to transcript file
        target_chars: Target character count for condensed message (default 300)
    """
    debug_log(f"=== Smart Mode Started (target: {target_chars} chars) ===")
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
            max_tokens=100,  # Allow longer condensed messages
            temperature=0,
            messages=[{
                "role": "user",
                "content": f"""Condense this message to approximately {target_chars} characters while preserving key information.

Focus on:
- What action Claude just completed
- Any important details or results
- What Claude is waiting for (if applicable)

Keep the response concise and informative.

Claude's message:
{context}"""
            }]
        )

        # Extract the response
        if message.content and len(message.content) > 0:
            response = message.content[0].text.strip()
            # Remove any quotes or extra formatting
            response = response.strip('"\'')
            debug_log(f"SUCCESS: API returned ({len(response)} chars): {response}")
            # Allow slight overflow beyond target
            return response[:target_chars + 50]

        debug_log("FAIL: API returned empty content")
        return None

    except Exception as e:
        # Silently fail and fall back to simple mode
        debug_log(f"FAIL: Exception in smart mode: {type(e).__name__}: {str(e)}")
        return None


def get_task_description_for_slack(hook_data: dict) -> str:
    """
    Hybrid approach: Use full message for short texts, smart condensing for long messages.

    - Messages <= SHORT_MESSAGE_THRESHOLD chars: Use full text (no API call)
    - Messages > SHORT_MESSAGE_THRESHOLD chars: Use smart AI condensing
    - Fallback: Truncate to threshold if smart mode fails
    """
    event = hook_data.get('hook_event_name', '')
    transcript_path = hook_data.get('transcript_path', '')

    # Handle UserPromptSubmit - user's message
    if event == 'UserPromptSubmit':
        user_prompt = hook_data.get('prompt', '')
        if user_prompt:
            # Truncate long user messages
            if len(user_prompt) > SHORT_MESSAGE_THRESHOLD:
                return user_prompt[:SHORT_MESSAGE_THRESHOLD] + "..."
            return user_prompt
        return "User submitted a message"

    # Handle PostToolUse - tool was approved and completed
    elif event == 'PostToolUse':
        tool_name = hook_data.get('tool_name', 'unknown')
        tool_input = hook_data.get('tool_input', {})

        if tool_name == 'Write':
            file_path = tool_input.get('file_path', 'a file')
            return f"✓ Wrote to {file_path}"
        elif tool_name == 'Edit':
            file_path = tool_input.get('file_path', 'a file')
            return f"✓ Edited {file_path}"
        elif tool_name == 'Bash':
            command = tool_input.get('command', 'a command')[:100]
            return f"✓ Ran: {command}"
        else:
            return f"✓ Used {tool_name}"

    # Handle events without transcripts
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

    # For Stop and Notification events with transcripts
    if not transcript_path:
        return "Claude is waiting for your input"

    # Extract full message
    full_message = read_last_claude_message(transcript_path)

    # Check message length
    if len(full_message) <= SHORT_MESSAGE_THRESHOLD:
        # Short message - use as-is (no API call, instant)
        debug_log(f"Message short ({len(full_message)} chars), using full text")
        result = full_message
    else:
        # Long message - use smart condensing
        debug_log(f"Message long ({len(full_message)} chars), using smart condensing")
        smart_summary = get_smart_description(transcript_path, target_chars=SMART_SUMMARY_TARGET)

        if smart_summary:
            result = smart_summary
        else:
            # Fallback: truncate to threshold
            debug_log("Smart mode failed, truncating to threshold")
            result = full_message[:SHORT_MESSAGE_THRESHOLD] + "..."

    # Add "(needs approval)" suffix for Notification events
    if event == 'Notification':
        result = f"{result} (needs approval)"

    # Ensure we don't exceed Slack's limits
    if len(result) > MAX_SLACK_LENGTH:
        result = result[:MAX_SLACK_LENGTH - 3] + "..."

    return result


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


def ensure_slack_channel_exists(channel_name: str, bot_token: str) -> bool:
    """
    Check if Slack channel exists, create if it doesn't.
    Returns True if channel exists or was created successfully.
    """
    try:
        # Check if channel exists by searching
        search_url = "https://slack.com/api/conversations.list"
        search_params = {
            "types": "private_channel",
            "limit": 1000
        }
        headers = {
            "Authorization": f"Bearer {bot_token}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        # Build query string
        query = '&'.join([f"{k}={v}" for k, v in search_params.items()])
        search_req = urllib.request.Request(
            f"{search_url}?{query}",
            headers=headers,
            method='GET'
        )

        with urllib.request.urlopen(search_req, timeout=5) as response:
            result = json.loads(response.read().decode('utf-8'))
            if result.get('ok'):
                # Check if channel with this name exists
                for channel in result.get('channels', []):
                    if channel.get('name') == channel_name:
                        debug_log(f"Channel #{channel_name} already exists")
                        return True

        # Channel doesn't exist, create it
        debug_log(f"Creating channel #{channel_name}...")
        create_url = "https://slack.com/api/conversations.create"
        create_payload = {
            "name": channel_name,
            "is_private": True
        }

        create_req = urllib.request.Request(
            create_url,
            data=json.dumps(create_payload).encode('utf-8'),
            headers={
                "Authorization": f"Bearer {bot_token}",
                "Content-Type": "application/json; charset=utf-8"
            },
            method='POST'
        )

        with urllib.request.urlopen(create_req, timeout=5) as response:
            result = json.loads(response.read().decode('utf-8'))
            if result.get('ok'):
                channel_id = result.get('channel', {}).get('id')
                debug_log(f"✓ Created channel #{channel_name} (ID: {channel_id})")

                # Invite the user to the newly created channel
                user_id = os.environ.get('SLACK_USER_ID')
                if user_id and channel_id:
                    invite_url = "https://slack.com/api/conversations.invite"
                    invite_payload = {
                        "channel": channel_id,
                        "users": user_id
                    }
                    invite_req = urllib.request.Request(
                        invite_url,
                        data=json.dumps(invite_payload).encode('utf-8'),
                        headers={
                            "Authorization": f"Bearer {bot_token}",
                            "Content-Type": "application/json; charset=utf-8"
                        },
                        method='POST'
                    )
                    try:
                        with urllib.request.urlopen(invite_req, timeout=5) as invite_response:
                            invite_result = json.loads(invite_response.read().decode('utf-8'))
                            if invite_result.get('ok'):
                                debug_log(f"✓ Invited user to #{channel_name}")
                            else:
                                debug_log(f"Failed to invite user: {invite_result.get('error', 'unknown')}")
                    except Exception as e:
                        debug_log(f"Error inviting user: {str(e)}")

                return True
            else:
                error = result.get('error', 'unknown')
                debug_log(f"Failed to create channel: {error}")

                # If channel name is taken, it exists but we might not be able to see it
                # Try to proceed anyway - posting might still work
                if error == 'name_taken':
                    debug_log(f"Channel {channel_name} already exists, proceeding to post")
                    return True  # Proceed anyway

                return False

    except Exception as e:
        debug_log(f"Error ensuring channel exists: {type(e).__name__}: {str(e)}")
        return False


def send_to_slack_channel(notification: dict, hook_data: dict) -> bool:
    """
    Send notification to Slack channel (claude_{user_id}_{repo_name}).
    Automatically creates the channel if it doesn't exist.
    Uses hybrid approach: full text for short messages, smart condensing for long messages.
    Returns True if successful, False otherwise.
    Silently fails if not configured, channel creation fails, or on error (won't block hook).
    """
    bot_token = os.environ.get('SLACK_BOT_TOKEN')
    cwd = notification.get('code_session_path', '')

    if not bot_token or not cwd:
        return False  # Silently skip if not configured

    # Build channel name from repo
    channel_name = get_slack_channel(cwd)
    debug_log(f"Target channel: #{channel_name}")

    # Ensure channel exists (create if needed)
    if not ensure_slack_channel_exists(channel_name, bot_token):
        debug_log(f"Skipping notification - channel doesn't exist and couldn't be created")
        return False

    try:
        # Map event to emoji
        event = notification.get('event', 'Unknown')
        emoji_map = {
            'Stop': '🟡',
            'Notification': '🔔',
            'PreToolUse': '🔵',
            'PostToolUse': '🛠️',
            'UserPromptSubmit': '👤',
            'SessionEnd': '⚫'
        }
        emoji = emoji_map.get(event, '⚪')

        # Generate task description using hybrid approach (for Slack)
        task = get_task_description_for_slack(hook_data)

        # Add @mention for Stop and Notification events (Claude's important updates)
        user_id = os.environ.get('SLACK_USER_ID')
        if event in ('Stop', 'Notification') and user_id:
            message = f"<@{user_id}> {emoji} {task}"
        else:
            message = f"{emoji} {task}"

        # Simple message with just emoji and task
        payload = {
            "channel": channel_name,  # Send to channel (not DM)
            "text": message
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
            'task': generate_task_description(hook_data),  # For file notifications
            'event': hook_data.get('hook_event_name', ''),
            'transcript_path': hook_data.get('transcript_path', ''),
        }

        # Write to notification file
        write_notification(notification)

        # Send to Slack channel (uses hybrid approach for better messages)
        send_to_slack_channel(notification, hook_data)

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
