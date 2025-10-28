#!/usr/bin/env python3
"""
Test Slack bot configuration and get your user ID

Usage:
    SLACK_BOT_TOKEN=xoxb-... python3 test-slack.py

Or set in .claude/settings.json:
    {
      "env": {
        "SLACK_BOT_TOKEN": "xoxb-..."
      }
    }
"""
import json
import os
import sys
import urllib.request
import urllib.error


def test_bot_connection():
    """Test bot token and get user info"""
    bot_token = os.environ.get('SLACK_BOT_TOKEN')

    if not bot_token:
        print("❌ ERROR: SLACK_BOT_TOKEN environment variable not set")
        print("\nSet it in one of these ways:")
        print("  1. Environment: export SLACK_BOT_TOKEN=xoxb-...")
        print("  2. Settings: Add to .claude/settings.json env section")
        sys.exit(1)

    if not bot_token.startswith('xoxb-'):
        print("⚠️  WARNING: Token should start with 'xoxb-'")
        print(f"   Your token starts with: {bot_token[:10]}...")

    try:
        # Test: Call auth.test to verify token and get user info
        url = "https://slack.com/api/auth.test"
        headers = {
            "Authorization": f"Bearer {bot_token}",
            "Content-Type": "application/json; charset=utf-8"
        }

        req = urllib.request.Request(url, headers=headers)

        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))

            if data.get('ok'):
                print("✅ Bot connected successfully!\n")
                print(f"📛 Bot name: {data.get('user', 'Unknown')}")
                print(f"👤 Bot user: @{data.get('user', 'unknown')}")
                print(f"🏢 Workspace: {data.get('team', 'Unknown')}")
                print(f"🆔 Bot user ID: {data.get('user_id', 'Unknown')}")
                print("\n" + "="*60)
                print("⚠️  NOTE: This is the BOT's user ID, not yours!")
                print("="*60)
                print("\nTo get YOUR user ID:")
                print("  1. In Slack, click your profile picture")
                print("  2. Click 'Profile'")
                print("  3. Click '...' (More)")
                print("  4. Click 'Copy member ID'")
                print("\nThen add BOTH to .claude/settings.json:")
                print('  "env": {')
                print(f'    "SLACK_BOT_TOKEN": "{bot_token[:20]}...",')
                print('    "SLACK_USER_ID": "U0G9QF9C6"  // YOUR user ID (starts with U)')
                print('  }')

                return True
            else:
                error = data.get('error', 'Unknown error')
                print(f"❌ Error: {error}")

                if error == 'invalid_auth':
                    print("\n💡 Tip: Check that your token is correct and hasn't expired")
                elif error == 'missing_scope':
                    print("\n💡 Tip: Add required scopes: chat:write, users:read")

                return False

    except urllib.error.HTTPError as e:
        print(f"❌ HTTP Error: {e.code} {e.reason}")
        print(f"   Response: {e.read().decode('utf-8')}")
        return False

    except urllib.error.URLError as e:
        print(f"❌ Connection Error: {e.reason}")
        print("   Check your internet connection")
        return False

    except Exception as e:
        print(f"❌ Unexpected Error: {type(e).__name__}: {e}")
        return False


def test_send_message():
    """Test sending a message to a user"""
    bot_token = os.environ.get('SLACK_BOT_TOKEN')
    user_id = os.environ.get('SLACK_USER_ID')

    if not user_id:
        print("\n" + "="*60)
        print("ℹ️  To test sending a message, set SLACK_USER_ID")
        print("="*60)
        return False

    print(f"\n📤 Testing message send to user: {user_id}")

    try:
        payload = {
            "channel": user_id,
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "🧪 *Test Message from Claude Code Notifier*\n━━━━━━━━━━━━━━━━━━━━━"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "If you see this message, your Slack integration is working! ✅"
                    }
                }
            ],
            "text": "Test message from Claude Code Notifier"
        }

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

        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))

            if result.get('ok'):
                print("✅ Test message sent successfully!")
                print("\n🎉 Slack integration is fully configured!")
                print("   Check your Slack DMs for the test message.")
                return True
            else:
                error = result.get('error', 'Unknown error')
                print(f"❌ Failed to send message: {error}")

                if error == 'channel_not_found':
                    print("\n💡 Tip: Check that SLACK_USER_ID is correct (starts with U)")
                elif error == 'not_in_channel':
                    print("\n💡 Tip: The bot needs permission to message you")

                return False

    except Exception as e:
        print(f"❌ Error sending message: {type(e).__name__}: {e}")
        return False


def main():
    print("="*60)
    print("  Claude Code Notifier - Slack Configuration Test")
    print("="*60)
    print()

    # Test bot connection
    if not test_bot_connection():
        sys.exit(1)

    # Test sending message if user ID provided
    test_send_message()

    print("\n" + "="*60)
    print("  Configuration Summary")
    print("="*60)
    print("\n✅ SLACK_BOT_TOKEN:", "Set" if os.environ.get('SLACK_BOT_TOKEN') else "❌ Not set")
    print("✅ SLACK_USER_ID:", os.environ.get('SLACK_USER_ID', "❌ Not set"))
    print()


if __name__ == '__main__':
    main()
