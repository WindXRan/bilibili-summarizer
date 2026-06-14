# bilibili-text-extractor

从B站视频提取文本的两种方案对比：**截图OCR** vs **音频转文字(ASR)**

## Workflow

```
B站视频链接
    │
    ├── 方案A: 截图OCR
    │   ├── 下载视频流
    │   ├── ffmpeg 定时抽帧 (每5秒)
    │   ├── PaddleOCR 逐帧识别
    │   └── 合并去重 → 文本
    │
    ├── 方案B: 音频转文字 (ASR)
    │   ├── 下载音频流
    │   ├── ffmpeg 转 WAV (16kHz PCM)
    │   └── Whisper 识别 → 文本
    │
    └── 方案C: API字幕 (最快, 但非所有视频都有)
        └── 直接拉取B站字幕JSON → 文本
```

## Prerequisites

```bash
pip install -r requirements.txt
```

额外依赖:
- **OCR方案**: `pip install paddlepaddle paddleocr` (或 `easyocr`)
- **ASR方案**: 已内置 `faster-whisper`

系统需安装 `ffmpeg` 并加入 PATH。

## Usage

### 方案A: 截图OCR

```bash
python -m src.ocr <BV号或B站链接> [-o output.txt]
```

### 方案B: 音频转文字

```bash
# 优先API字幕, 无字幕自动ASR
python main.py <BV号或B站链接>

# 强制ASR
python main.py <BV号或B站链接> --asr

# 保存到文件
python main.py <BV号或B站链接> -o output.txt
```

### 方案C: API字幕

```bash
python main.py <BV号或B站链接>
# 有字幕的视频自动走此方案, 秒级返回
```

## 对比评估

对同一视频分别跑 OCR 和 ASR，评估维度:

| 维度 | OCR | ASR |
|------|-----|-----|
| 速度 | 抽帧+OCR (视频越大越慢) | 下载+Whisper (中速) |
| 中文准确率 | 依赖OCR引擎质量 | 较好 (Whisper) |
| 对文案类视频 | 能识别屏幕上的文字/代码 | 只能识别语音 |
| 对纯语音视频 | 几乎无效 | 效果好 |
| 网络消耗 | 下载完整视频 (较大) | 仅下载音频 (较小) |
| 硬件要求 | CPU可跑, GPU更快 | CPU可跑, GPU更快 |

## 目录结构

```
src/
├── __init__.py
├── bilibili_text.py   # 入口: 解析BV → 字幕/ASR
├── transcriber.py     # ASR: 下载音频 + Whisper
└── ocr.py             # OCR: 下载视频 + 抽帧 + OCR
tmp/models/            # Whisper模型缓存
```

## 最佳实践

1. **有字幕的视频** → 直接用 API 字幕 (方案C), 秒级出结果
2. **语音讲解类视频** → ASR (方案B), Whisper 对中文语音识别度较高
3. **屏幕录制/代码演示类** → OCR (方案A), 能捕捉屏幕上的文字
4. **混合型** → 两种都跑, 取交集或合并
