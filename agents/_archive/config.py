"""
Agent Configuration
Load settings from environment variables
"""

import os
from dotenv import load_dotenv

load_dotenv()

# LiveKit Configuration
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "ws://localhost:7880")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")

# OpenClaw Bridge
OPENCLAW_BRIDGE_URL = os.getenv("OPENCLAW_BRIDGE_URL", "http://localhost:3000")
OPENCLAW_API_KEY = os.getenv("OPENCLAW_API_KEY", "")

# Speech-to-Text (Deepgram)
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")

# Text-to-Speech (Cartesia)
CARTESIA_API_KEY = os.getenv("CARTESIA_API_KEY", "")

# LLM (for development, production uses router)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Agent Settings
DEFAULT_MODEL = "gpt-4o-mini"  # T1 equivalent for LiveKit
DEFAULT_VOICE = "79a125e8-cd45-4c13-8a67-188112f4dd22"  # Cartesia voice ID
DEFAULT_LANGUAGE = "en-US"

# Validation
def validate_config():
    """Validate required configuration"""
    required = {
        "LIVEKIT_URL": LIVEKIT_URL,
        "LIVEKIT_API_KEY": LIVEKIT_API_KEY,
        "LIVEKIT_API_SECRET": LIVEKIT_API_SECRET,
        "DEEPGRAM_API_KEY": DEEPGRAM_API_KEY,
    }

    missing = [key for key, value in required.items() if not value]

    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    print("[Config] Validation passed")

if __name__ == "__main__":
    validate_config()
