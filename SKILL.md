# bilibili-text

Extract text from Bilibili videos — instantly via API subtitles, or fallback to ASR.

## Workflow

```
链接 → API字幕? → 有 → 输出文案 (几KB, 秒级)
               → 无 → 下载音频 → Whisper 识别 → 输出文案 (需下载音频, 耗时较长)
```

## Prerequisites

```bash
pip install -r requirements.txt
```

## Usage

```bash
# 1) Try API subtitles first (fastest, zero download)
python main.py "https://www.bilibili.com/video/BV1xx411c7mD"

# 2) Force ASR (audio download + whisper)
python main.py "BV1xx411c7mD" --asr

# 3) Save to file
python main.py "BV1xx411c7mD" -o output.txt

# 4) ASR + save
python main.py "BV1xx411c7mD" --asr -o output.txt
```

## Notes

- **API 字幕**: 有字幕的视频直接拉取字幕 JSON，秒级完成，几乎不耗流量
- **ASR 模式**: 无字幕视频自动 fallback，或 `--asr` 强制使用。需下载音频 (几MB) + 本地 Whisper 识别
- 第一次运行 ASR 会自动下载 Whisper 模型 (tiny, ~150MB)
