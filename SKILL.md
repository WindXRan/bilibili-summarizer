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
# 优先API字幕, 无字幕自动ASR → project/{作者}/{视频名}.txt
python main.py <BV号或B站链接>

# 强制ASR (跳过字幕检测)
python main.py <BV号或B站链接> --asr

# 一键 TTS 转音频 (txt + mp3 都保存)
python main.py <BV号或B站链接> --asr --tts

# 自定义路径 (跳过 project/ 结构)
python main.py <BV号或B站链接> -o my.txt
```

## 输出结构

```
project/
  ├─ 作者名1/
  │   ├─ 视频标题1.txt
  │   ├─ 视频标题1.mp3
  │   ├─ 视频标题2.txt
  │   └─ ...
  └─ 作者名2/
      └─ ...
```

## 注意事项

- **API字幕**: 有字幕的视频秒级返回
- **ASR模式**: 首次运行会自动下载 Whisper 模型 (tiny, ~150MB)
- **TTS模式**: `--tts` 自动调用 edge-tts 生成 MP3，默认音色 `zh-CN-XiaoxiaoNeural`
- **洗稿**: 提取后人工修改 txt，再用 edge-tts 转音频
- 只需下载音频流（几MB到几十MB），无需下载完整视频
