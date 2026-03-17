"""
Meeting audio transcription using OpenAI GPT-4o mini Transcribe.

Converts audio to raw text only. Meeting summarization and analysis
is handled by Claude in the doc-orchestrator skill.

Usage:
    python scripts/transcribe.py <audio_file_path> <output_path>

Requirements:
    pip install openai

Environment:
    OPENAI_API_KEY must be set
"""

import sys
import json
import os
from datetime import datetime
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    print("Error: openai package not installed. Run: pip install openai")
    sys.exit(1)


SUPPORTED_FORMATS = {".mp3", ".mp4", ".wav", ".m4a", ".webm", ".ogg", ".flac"}


def transcribe(audio_file_path: str) -> dict:
    """Transcribe meeting audio using GPT-4o mini Transcribe."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set")
        sys.exit(1)

    path = Path(audio_file_path)

    if not path.exists():
        print(f"Error: File not found: {audio_file_path}")
        sys.exit(1)

    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_FORMATS:
        print(f"Error: Unsupported format '{suffix}'. Supported: {', '.join(SUPPORTED_FORMATS)}")
        sys.exit(1)

    client = OpenAI(api_key=api_key)

    with open(path, "rb") as audio_file:
        response = client.audio.transcriptions.create(
            model="gpt-4o-transcribe",
            file=audio_file,
            response_format="json",
        )

    return {
        "transcript": response.text,
        "source_file": audio_file_path,
        "processed_at": datetime.now().isoformat(),
    }


def main():
    if len(sys.argv) != 3:
        print("Usage: python scripts/transcribe.py <audio_file_path> <output_path>")
        sys.exit(1)

    audio_file_path = sys.argv[1]
    output_path = sys.argv[2]

    print(f"Transcribing: {audio_file_path}")
    result = transcribe(audio_file_path)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with open(output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"Transcript saved: {output_path}")
    print(f"Length: {len(result['transcript'])} characters")


if __name__ == "__main__":
    main()
