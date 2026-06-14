# bilibili-text

Extract text/subtitles from Bilibili videos via API — no video/audio download needed.

## Usage

```bash
# Fetch subtitle text from a Bilibili video
python -m src.bilibili_text "https://www.bilibili.com/video/BV1xx411c7mD"

# Or just BV number
python -m src.bilibili_text "BV1xx411c7mD"

# Save to file
python -m src.bilibili_text "BV1xx411c7mD" -o output.txt
```

## How it works

1. Calls Bilibili's public JSON API to get video info (`cid`)
2. Fetches subtitle track list from the player API
3. Downloads the subtitle JSON (a few KB) — no video/audio ever downloaded
4. Outputs clean text

## Requirements

- Python 3.9+
- `pip install requests`

## Notes

- Only works for videos that have subtitle tracks (AI-generated or uploaded subtitles)
- For videos without subtitles, consider using `bili2text` (https://github.com/lanbinleo/bili2text) with Whisper ASR
- No login/cookies required for most public videos
