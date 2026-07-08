#!/usr/bin/env python3
"""
Safe OpenAI API Key Updater
Helps update the .env file with a real OpenAI API key.
"""

import os
import re
from pathlib import Path

def update_api_key():
    """Safely update the OpenAI API key in the .env file"""

    env_path = Path(__file__).parent / "app" / ".env"

    if not env_path.exists():
        print("❌ .env file not found!")
        return False

    print("🔑 OpenAI API Key Updater")
    print("=" * 40)
    print("Current .env file location:", env_path)

    # Read current content
    with open(env_path, 'r') as f:
        content = f.read()

    # Find current API key line
    api_key_match = re.search(r'OPENAI_API_KEY=(.+)', content)
    if not api_key_match:
        print("❌ Could not find OPENAI_API_KEY in .env file")
        return False

    current_key = api_key_match.group(1).strip()
    print(f"Current API key: {current_key[:20]}...")

    # Get new API key from user
    print("\n📝 Enter your OpenAI API key:")
    print("(It should start with 'sk-' and be around 51 characters long)")
    print("(Your input will be hidden for security)")

    # Use getpass for secure input
    try:
        import getpass
        new_key = getpass.getpass("OpenAI API Key: ").strip()
    except ImportError:
        # Fallback if getpass not available
        new_key = input("OpenAI API Key: ").strip()

    # Validate the new key
    if not new_key:
        print("❌ No API key entered")
        return False

    if not new_key.startswith("sk-"):
        print("❌ API key must start with 'sk-'")
        return False

    if len(new_key) < 40:
        print("❌ API key seems too short (should be ~51 characters)")
        return False

    # Update the content
    updated_content = content.replace(
        f"OPENAI_API_KEY={current_key}",
        f"OPENAI_API_KEY={new_key}"
    )

    # Write back to file
    with open(env_path, 'w') as f:
        f.write(updated_content)

    print("✅ API key updated successfully!")
    print("🔄 Please restart the backend server for changes to take effect")
    print("\nTo restart the server:")
    print("  cd backend && python3 run_server.py")

    return True

if __name__ == "__main__":
    try:
        update_api_key()
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled")
    except Exception as e:
        print(f"❌ Error: {e}")