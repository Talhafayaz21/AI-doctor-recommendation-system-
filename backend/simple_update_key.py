#!/usr/bin/env python3
"""
Simple OpenAI API Key Updater
"""

import os
import re
from pathlib import Path

def update_api_key():
    """Update the OpenAI API key in .env file"""

    env_path = Path(__file__).parent / "app" / ".env"

    print("🔑 OpenAI API Key Updater")
    print("=" * 40)
    print(f"Updating .env file at: {env_path}")

    # Get the API key from user
    print("\n📝 Please enter your OpenAI API key:")
    print("(Go to https://platform.openai.com/account/api-keys to get it)")
    print("(It should start with 'sk-' and be around 51 characters)")

    new_key = input("API Key: ").strip()

    if not new_key:
        print("❌ No API key entered")
        return False

    if not new_key.startswith("sk-"):
        print("❌ API key must start with 'sk-'")
        return False

    if len(new_key) < 40:
        print("❌ API key seems too short")
        return False

    # Read current .env content
    with open(env_path, 'r') as f:
        content = f.read()

    # Replace the API key line
    old_pattern = r'OPENAI_API_KEY=.+'
    new_line = f'OPENAI_API_KEY={new_key}'

    if re.search(old_pattern, content):
        updated_content = re.sub(old_pattern, new_line, content)

        # Write back
        with open(env_path, 'w') as f:
            f.write(updated_content)

        print("✅ API key updated successfully!")
        print("🔄 Please restart the backend server")
        return True
    else:
        print("❌ Could not find OPENAI_API_KEY line in .env")
        return False

if __name__ == "__main__":
    try:
        update_api_key()
    except Exception as e:
        print(f"❌ Error: {e}")