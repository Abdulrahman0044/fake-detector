import asyncio
import os
import subprocess
import math
import shutil
from pathlib import Path
from dotenv import load_dotenv
from realitydefender import RealityDefender, RealityDefenderError

load_dotenv()

API_KEY = os.environ.get("REALITY_DEFENDER_API_KEY")
VIDEO_PATH = os.environ.get("VIDEO_PATH_URL")  # source video
WORKDIR = Path("audio_check_output")          # where extracted audio goes
SEGMENT_LENGTH_SEC = 30                       # length of each chunk in segment mode


def ensure_ffmpeg_available() -> None:
    """Ensure the FFmpeg binaries are installed and available on PATH."""
    missing = [tool for tool in ("ffmpeg", "ffprobe") if shutil.which(tool) is None]
    if missing:
        raise RuntimeError(
            "FFmpeg is not installed or not on PATH. Install FFmpeg and restart your terminal. "
            "On Windows, try: winget install Gyan.Dev.FFmpeg or choco install ffmpeg. "
            f"Missing tools: {', '.join(missing)}"
        )


def extract_full_audio(video_path: str, out_path: Path) -> Path:
    """Extract the entire audio track from the video as an MP3."""
    ensure_ffmpeg_available()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-acodec", "libmp3lame", "-q:a", "2",
        str(out_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return out_path


def get_duration_seconds(video_path: str) -> float:
    """Use ffprobe to get the video's duration in seconds."""
    ensure_ffmpeg_available()
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", video_path,
    ]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return float(result.stdout.strip())


def extract_audio_segments(video_path: str, out_dir: Path, segment_len: int) -> list[tuple[float, float, Path]]:
    """Split the audio track into fixed-length chunks, returning (start, end, path) tuples."""
    out_dir.mkdir(parents=True, exist_ok=True)
    duration = get_duration_seconds(video_path)
    n_segments = math.ceil(duration / segment_len)

    segments = []
    for i in range(n_segments):
        start = i * segment_len
        end = min(start + segment_len, duration)
        seg_path = out_dir / f"segment_{i:03d}_{int(start)}s-{int(end)}s.mp3"
        cmd = [
            "ffmpeg", "-y", "-ss", str(start), "-i", video_path,
            "-t", str(end - start),
            "-vn", "-acodec", "libmp3lame", "-q:a", "2",
            str(seg_path),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        segments.append((start, end, seg_path))

    return segments


async def scan_file(rd: RealityDefender, file_path: Path) -> dict:
    """Upload a single audio file and return the detection result."""
    upload = await rd.upload(file_path=str(file_path))
    result = await rd.get_result(upload["request_id"])
    return result


def print_result(label: str, result: dict) -> None:
    score = result.get("score")
    score_disp = f"{score:.4f} ({score * 100:.1f}%)" if score is not None else "N/A"
    print(f"\n--- {label} ---")
    print(f"Status: {result['status']}")
    print(f"Score:  {score_disp}")
    for m in result.get("models", []):
        s = m["score"]
        s_disp = f"{s:.4f} ({s * 100:.1f}%)" if s is not None else "N/A"
        print(f"   - {m['name']}: {m['status']} (score: {s_disp})")


async def run_whole_file_check() -> None:
    full_audio_path = WORKDIR / "full_audio.mp3"
    print(f"Extracting full audio track to {full_audio_path} ...")
    extract_full_audio(VIDEO_PATH, full_audio_path)

    rd = RealityDefender(api_key=API_KEY)
    try:
        print("Uploading full audio track for analysis...")
        result = await scan_file(rd, full_audio_path)
        print_result("Full Audio Track", result)
    except RealityDefenderError as e:
        print(f"Reality Defender error: {e.message} (code: {e.code})")


async def run_segment_check() -> None:
    seg_dir = WORKDIR / "segments"
    print(f"Splitting audio into {SEGMENT_LENGTH_SEC}s segments in {seg_dir} ...")
    segments = extract_audio_segments(VIDEO_PATH, seg_dir, SEGMENT_LENGTH_SEC)
    print(f"Created {len(segments)} segments.")

    rd = RealityDefender(api_key=API_KEY)
    for start, end, path in segments:
        label = f"Segment {int(start)}s\u2013{int(end)}s ({path.name})"
        try:
            print(f"\nUploading {path.name} ...")
            result = await scan_file(rd, path)
            print_result(label, result)
        except RealityDefenderError as e:
            print(f"\n--- {label} ---")
            print(f"Reality Defender error: {e.message} (code: {e.code})")


async def main() -> None:
    if not API_KEY:
        print("ERROR: REALITY_DEFENDER_API_KEY not found. Check your .env file.")
        return

    try:
        ensure_ffmpeg_available()
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        return

    print("Choose a mode:")
    print("  1 = Check the whole audio track at once")
    print("  2 = Split into segments and check each (helps localize a disputed portion)")
    choice = input("Enter 1 or 2: ").strip()

    if choice == "2":
        await run_segment_check()
    else:
        await run_whole_file_check()


if __name__ == "__main__":
    asyncio.run(main())