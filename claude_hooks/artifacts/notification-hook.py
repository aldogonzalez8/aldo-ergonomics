#!/usr/bin/env python3
"""
Claude Code notification hook - writes session status to a notification file

Smart Mode (Optional):
  Set ANTHROPIC_API_KEY environment variable to enable smart LLM-based descriptions.
  Requires: pip install anthropic
  Falls back to simple text parsing if not available.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


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


def get_smart_description(transcript_path: str, max_chars: int = 1000) -> str | None:
    """
    Use Claude API to generate a smart, concise description of what Claude just did.
    Returns None if API key not available or if request fails.
    """
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        return None

    try:
        # Import anthropic only if API key is available
        import anthropic

        # Read the last few messages from transcript
        transcript = Path(transcript_path).expanduser()
        if not transcript.exists():
            return None

        lines = transcript.read_text().strip().split('\n')

        # Get last few assistant and user messages
        messages_text = []
        for line in reversed(lines[-10:]):  # Last 10 lines
            try:
                entry = json.loads(line)
                # Claude Code transcript format uses "type" instead of "role"
                role = entry.get('type', '')

                # Content is nested in message.content for Claude Code transcripts
                content = None
                if 'message' in entry and isinstance(entry['message'], dict):
                    content = entry['message'].get('content', [])
                else:
                    content = entry.get('content', [])

                if role in ['assistant', 'user']:
                    # Extract text from content
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get('type') == 'text':
                                text = block.get('text', '').strip()
                                if text:
                                    messages_text.append(f"{role}: {text[:300]}")
                    elif isinstance(content, str):
                        messages_text.append(f"{role}: {content[:300]}")
            except:
                continue

        if not messages_text:
            return None

        # Reverse to get chronological order
        messages_text = list(reversed(messages_text))
        context = "\n".join(messages_text[-5:])  # Last 5 messages

        # Use Claude API with very short timeout
        client = anthropic.Anthropic(api_key=api_key, timeout=3.0)

        message = client.messages.create(
            model="claude-3-5-haiku-20241022",  # Fast, cheap model
            max_tokens=50,
            temperature=0,
            messages=[{
                "role": "user",
                "content": f"Summarize what the AI assistant (Claude) just did or created in 10-15 words. Focus on code changes, files modified, or tasks completed. Be direct and factual:\n\n{context}"
            }]
        )

        # Extract the response
        if message.content and len(message.content) > 0:
            response = message.content[0].text.strip()
            # Remove any quotes or extra formatting
            response = response.strip('"\'')
            return response[:150]

        return None

    except Exception as e:
        # Silently fail and fall back to simple mode
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
                return smart_desc
            # Fall back to simple parsing
            return read_last_claude_message(transcript_path)
        return "Claude is waiting for your input"

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
