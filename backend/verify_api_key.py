#!/usr/bin/env python3
"""
Verify OpenAI API Key Configuration
Tests if the API key is properly set and can authenticate with OpenAI.
"""

import os
from pathlib import Path

def verify_api_key():
    """Verify the OpenAI API key configuration"""

    print("🔍 OpenAI API Key Verification")
    print("=" * 40)

    # Load environment
    env_path = Path(__file__).parent / "app" / ".env"
    if env_path.exists():
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=env_path)
        print("✅ .env file loaded")
    else:
        print("❌ .env file not found")
        return False

    # Check API key
    api_key = os.getenv('OPENAI_API_KEY')

    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment")
        return False

    if api_key == 'YOUR_ACTUAL_OPENAI_API_KEY_HERE' or 'placeholder' in api_key.lower():
        print("❌ API key is still a placeholder - please set your real API key")
        return False

    if not api_key.startswith('sk-'):
        print("❌ API key must start with 'sk-'")
        return False

    if len(api_key) < 40:
        print("❌ API key seems too short (should be ~51 characters)")
        return False

    print("✅ API key format looks correct")

    # Try to authenticate with OpenAI (optional)
    try:
        from app.rag.embeddings import is_available
        if is_available():
            print("✅ OpenAI client can authenticate successfully")
            print("🎉 RAG system is ready to use!")
            return True
        else:
            print("❌ OpenAI authentication failed")
            print("   - Check if your API key is valid")
            print("   - Verify your OpenAI account has credits")
            return False
    except Exception as e:
        print(f"❌ Error testing authentication: {e}")
        return False

if __name__ == "__main__":
    verify_api_key()