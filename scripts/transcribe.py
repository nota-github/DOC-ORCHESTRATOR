"""
Meeting audio transcription using OpenAI GPT-4o Transcribe.

Converts audio to raw text only. Meeting summarization and analysis
is handled by Claude in the doc-orchestrator skill.

Supports long audio files by automatically chunking them into segments
under the API's 1400-second limit.

Usage:
    python scripts/transcribe.py <audio_file_path> <output_path>

Requirements:
    - ffmpeg (for audio duration detection and chunking)
    - pip install openai

Environment:
    OPENAI_API_KEY must be set
"""

import sys
import json
import os
import subprocess
import tempfile
import shutil
from datetime import datetime, timezone, timedelta

# Korea Standard Time (UTC+9)
KST = timezone(timedelta(hours=9))
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    print("Error: openai package not installed. Run: pip install openai")
    sys.exit(1)


SUPPORTED_FORMATS = {".mp3", ".mp4", ".wav", ".m4a", ".webm", ".ogg", ".flac"}
MAX_DURATION_SECONDS = 1300  # Leave buffer below 1400s API limit


def get_audio_duration(audio_path: Path) -> float:
    """Get audio duration in seconds using ffprobe."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")
    return float(result.stdout.strip())


def split_audio(audio_path: Path, chunk_duration: int, output_dir: Path) -> list[Path]:
    """Split audio file into chunks using ffmpeg."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Use same extension as input for compatibility
    ext = audio_path.suffix
    output_pattern = output_dir / f"chunk_%03d{ext}"

    result = subprocess.run(
        [
            "ffmpeg",
            "-i", str(audio_path),
            "-f", "segment",
            "-segment_time", str(chunk_duration),
            "-c", "copy",  # No re-encoding, fast
            "-reset_timestamps", "1",
            str(output_pattern),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg split failed: {result.stderr}")

    # Return sorted list of chunk files
    chunks = sorted(output_dir.glob(f"chunk_*{ext}"))
    return chunks


def transcribe_single(client: OpenAI, audio_path: Path) -> str:
    """Transcribe a single audio file."""
    with open(audio_path, "rb") as audio_file:
        response = client.audio.transcriptions.create(
            model="gpt-4o-transcribe",
            file=audio_file,
            response_format="json",
        )
    return response.text


def transcribe(audio_file_path: str) -> dict:
    """Transcribe meeting audio using GPT-4o Transcribe.

    Automatically chunks long audio files that exceed the API limit.
    """
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

    # Check duration
    duration = get_audio_duration(path)
    print(f"Audio duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")

    if duration <= MAX_DURATION_SECONDS:
        # Short audio - transcribe directly
        transcript = transcribe_single(client, path)
        chunks_info = None
    else:
        # Long audio - split and transcribe chunks
        num_chunks = int(duration // MAX_DURATION_SECONDS) + 1
        print(f"Audio exceeds {MAX_DURATION_SECONDS}s limit, splitting into {num_chunks} chunks...")

        temp_dir = Path(tempfile.mkdtemp(prefix="transcribe_"))
        try:
            chunks = split_audio(path, MAX_DURATION_SECONDS, temp_dir)
            print(f"Created {len(chunks)} chunks")

            transcripts = []
            for i, chunk in enumerate(chunks):
                print(f"Transcribing chunk {i+1}/{len(chunks)}...")
                chunk_transcript = transcribe_single(client, chunk)
                transcripts.append(chunk_transcript)

            # Join transcripts with spacing
            transcript = "\n\n".join(transcripts)
            chunks_info = {
                "count": len(chunks),
                "chunk_duration_seconds": MAX_DURATION_SECONDS,
            }
        finally:
            # Clean up temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)

    result = {
        "transcript": transcript,
        "source_file": audio_file_path,
        "duration_seconds": duration,
        "processed_at": datetime.now(KST).isoformat(),
    }

    if chunks_info:
        result["chunks"] = chunks_info

    return result


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
