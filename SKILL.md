# bilibili-text-extractor

从B站视频提取文本 —— 优先API字幕，无字幕则走 Whisper ASR。

## Workflow

```
B站视频链接
    │
    ├── API字幕? → 有 → 直接拉取字幕JSON (秒级)
    │
    └── 无 → 下载音频流 → ffmpeg转WAV → Whisper ASR → 文本
```

## Prerequisites

```bash
pip install -r requirements.txt
```

系统需安装 `ffmpeg` 并加入 PATH。

## Usage

```bash
# 优先API字幕, 无字幕自动ASR
python main.py <BV号或B站链接>

# 强制ASR (跳过字幕检测)
python main.py <BV号或B站链接> --asr

# 保存到文件
python main.py <BV号或B站链接> -o output.txt
```

## 注意事项

- **API字幕**: 有字幕的视频秒级返回
- **ASR模式**: 首次运行会自动下载 Whisper 模型 (tiny, ~150MB)
- 只需下载音频流（几MB到几十MB），无需下载完整视频
