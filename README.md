# Fake Detector

This project checks whether a video or extracted audio has signs of manipulation using the Reality Defender API.

## Features

- Reads the API key from a `.env` file
- Extracts audio from a local video using FFmpeg
- Splits the audio into 30-second chunks for segment analysis
- Uploads either the full audio track or each segment for detection
- Prints status and score details for each analysis result

## Requirements

- Python 3.11+
- FFmpeg installed and available on your PATH
- A valid Reality Defender API key

## Setup

1. Create a virtual environment (optional but recommended):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install python-dotenv realitydefender
```

3. Create a `.env` file in the project root:

```env
REALITY_DEFENDER_API_KEY=your-api-key-here
```

4. Update the video path in `app.py` if needed or in the .env:

```python
VIDEO_PATH = "\VID-20260828-WA12.mp4"
```

5. Run the script:

```powershell
python app.py
```

## Project layout

- `app.py` — main analysis flow
- `.env` — local environment variables
- `audio_check_output/` — extracted audio and segment files

## Notes

- Do not commit your `.env` file.
- FFmpeg must be installed and accessible by name (`ffmpeg` and `ffprobe`).
- The app can analyze either the full audio track or segmented chunks.
