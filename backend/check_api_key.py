#!/usr/bin/env python3
"""
OpenAI API Key Setup Helper
Helps set up and test OpenAI API key configuration.
"""

import os
import sys
from pathlib import Path

def check_api_key():
    """Check if OpenAI API key is properly configured"""
    # Check .env file
    env_path = Path(__file__).parent / "app" / ".env"
    if not env_path.exists():
        print("❌ .env file not found")
        return False

    # Read .env file
    with open(env_path, 'r') as f:
        content = f.read()

    # Check for API key
    api_key_line = None
    for line in content.split('\n'):
        if line.startswith('OPENAI_API_KEY='):
            api_key_line = line
            break

    if not api_key_line:
        print("❌ OPENAI_API_KEY not found in .env file")
        return False

    api_key = api_key_line.split('=', 1)[1].strip()

    # Check if it's a placeholder
    if "your-" in api_key.lower() or "here" in api_key.lower() or not api_key.startswith('sk-'):
        print("❌ OPENAI_API_KEY appears to be a placeholder or invalid")
        print(f"   Current value: {api_key}")
        print("   Please replace with your actual OpenAI API key (starts with 'sk-')")
        return False

    print("✅ OpenAI API key appears to be properly configured")
    return True

def show_setup_instructions():
    """Show instructions for setting up the API key"""
    print("\n🔑 OpenAI API Key Setup Instructions:")
    print("=" * 50)
    print("1. Go to https://platform.openai.com/account/api-keys")
    print("2. Log in to your OpenAI account")
    print("3. Click 'Create new secret key'")
    print("4. Copy the API key (it starts with 'sk-')")
    print("5. Replace the placeholder in backend/app/.env:")
    print("   ")
    print("   OPENAI_API_KEY=sk-your-actual-api-key-here")
    print("   ")
    print("   With:")
    print("   ")
    print("   OPENAI_API_KEY=sk-...your-actual-key...")
    print("6. Restart the backend server")
    print()
    print("⚠️  Important:")
    print("   - Never share your API key publicly")
    print("   - The system will work without it using fallback methods")
    print("   - With a valid key, you'll get enhanced AI responses")

if __name__ == "__main__":
    print("OpenAI API Key Configuration Check")
    print("=" * 40)

    if check_api_key():
        print("\n🎉 Configuration looks good!")
        print("The system should now use OpenAI API for enhanced responses.")
    else:
        show_setup_instructions()