# bilibili-text-extractor

从B站视频提取文本 —— 优先API字幕，无字幕则走 Whisper ASR。

## Workflow (完整链路)

```
B站链接 → 提取文案 → AI洗稿(按prompts.md) → 渲染视频MP4
```

```
提取:  B站链接 → API字幕? → 有 → 字幕JSON
                          → 无 → 下载音频 → Whisper ASR → _asr.txt
洗稿:  _asr.txt → 用 prompts.md 里的洗稿Prompt → _洗稿.txt
切分:  _洗稿.txt → 用 prompts.md 里的切分Prompt → _分镜.json (可选)
渲染:  _洗稿.txt → 切分幻灯片 → HTML截图 → 配音 → ffmpeg → MP4
                     ︎ 逐句模式: --sentences (一句一画面)
                     ︎ 段落模式: 默认 (空行分段)
```

## Prerequisites

```bash
pip install -r requirements.txt
# GPU加速 (RTX 4060等N卡):
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
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

## 洗稿 & 渲染

先用 AI 按 `prompts.md` 中的提示词洗稿，然后渲染：

```bash
# 段落模式 (默认, 每组空行=一页)
python render.py "project/作者/标题_洗稿.txt"

# 逐句模式 (每行=一页, 适合一句一画面)
python render.py "project/作者/标题_洗稿.txt" --sentences

# 指定输出路径和音色
python render.py "project/作者/标题_洗稿.txt" -o final.mp4 --voice zh-CN-YunxiNeural
```

## 输出结构

```
project/
  ├─ 作者名1/
  │   ├─ 视频标题1.txt     # 文案 (洗稿前/后)
  │   ├─ 视频标题1.mp3     # TTS 配音
  │   ├─ 视频标题1.mp4     # 渲染视频(黑底白字)
  │   ├─ 视频标题2.txt
  │   └─ ...
  └─ 作者名2/
      └─ ...
```

## 注意事项

- **API字幕**: 有字幕的视频秒级返回
- **ASR模式**: 首次运行会自动下载 Whisper 模型 (默认 small, ~500MB)
- **GPU加速**: 有 N 卡会自动启用 CUDA；可在 `transcriber.py` 中调大模型:
  - `large-v3-turbo` (RTX 4060 8GB 推荐): 接近最高精度, 速度快
  - `large-v3`: 极致精度, 显存占用高
  - `small` (默认): CPU/GPU 通用
- **TTS模式**: `--tts` 自动调用 edge-tts 生成 MP3，默认音色 `zh-CN-XiaoxiaoNeural`
- **洗稿**: 提取后人工修改 txt，再用 edge-tts 转音频
- 只需下载音频流（几MB到几十MB），无需下载完整视频
