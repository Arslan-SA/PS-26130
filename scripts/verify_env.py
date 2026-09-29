#!/usr/bin/env python3
"""
Environment template verification script.
Ensures .env.example contains required core fields and parses cleanly.
"""
import sys
from pathlib import Path

REQUIRED_KEYS = [
    "PROJECT_NAME",
    "DATABASE_URL",
    "SECRET_KEY",
    "ALGORITHM",
    "API_V1_STR",
    "AI_PROVIDER",
    "OCR_ENGINE",
    "NEXT_PUBLIC_API_URL"
]

def main():
    root_dir = Path(__file__).resolve().parent.parent
    env_example = root_dir / ".env.example"
    
    if not env_example.exists():
        print("ERROR: .env.example not found!", file=sys.stderr)
        sys.exit(1)
        
    content = env_example.read_text(encoding="utf-8")
    found_keys = set()
    for line in content.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key = line.split("=", 1)[0].strip()
            found_keys.add(key)
            
    missing = [k for k in REQUIRED_KEYS if k not in found_keys]
    if missing:
        print(f"ERROR: Missing required keys in .env.example: {missing}", file=sys.stderr)
        sys.exit(1)
        
    print(f"SUCCESS: .env.example verified with {len(found_keys)} configuration keys.")
    sys.exit(0)

if __name__ == "__main__":
    main()
