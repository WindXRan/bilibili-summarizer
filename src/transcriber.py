import os
import shutil
import subprocess
import tempfile
from pathlib import Path

# Use HF mirror for Chinese networks, bypass SSL for proxy environments
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HUB_DISABLE_SSL_VERIFY", "1")

import httpx
from faster_whisper import WhisperModel


API_VIEW = "https://api.bilibili.com/x/web-interface/view"
API_PLAYURL = "https://api.bilibili.com/x/player/playurl"

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com",
    "Origin": "https://www.bilibili.com",
}

MODEL_SIZE = "tiny"
_output_dir: Path | None = None


def get_output_dir() -> Path:
    global _output_dir
    if _output_dir is None:
        _output_dir = Path(tempfile.mkdtemp(prefix="bili_"))
    _output_dir.mkdir(parents=True, exist_ok=True)
    return _output_dir


def download_audio(bvid: str) -> Path:
    out = get_output_dir()
    wav_path = out / f"{bvid}.wav"
    if wav_path.exists():
        return wav_path

    raw_path = out / f"{bvid}.m4s"

    with httpx.Client(headers=_HEADERS, follow_redirects=True, timeout=30) as c:
        info = c.get(API_VIEW, params={"bvid": bvid}).json()
        if info.get("code") != 0:
            raise RuntimeError(f"获取视频信息失败: {info.get('message')}")
        cid = info["data"]["cid"]

        play = c.get(API_PLAYURL, params={"bvid": bvid, "cid": cid, "fnval": 4048}).json()
        if play.get("code") != 0:
            raise RuntimeError(f"获取音频链接失败: {play.get('message')}")

        audio_streams = play["data"]["dash"]["audio"]
        audio_url = audio_streams[0]["baseUrl"]

        resp = c.get(audio_url, timeout=300)
        resp.raise_for_status()
        raw_path.write_bytes(resp.content)

    subprocess.run(
        ["ffmpeg", "-y", "-i", str(raw_path), "-acodec", "pcm_s16le", "-ar", "16000", str(wav_path)],
        capture_output=True, check=True,
    )
    raw_path.unlink(missing_ok=True)
    return wav_path


def _get_model_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "models" / MODEL_SIZE


def transcribe(audio_path: Path, language: str = "zh") -> str:
    model = WhisperModel(
        MODEL_SIZE,
        device="cpu",
        compute_type="int8",
        download_root=str(_get_model_dir()),
    )
    segments, _ = model.transcribe(str(audio_path), language=language, beam_size=1)
    return _format_segments(list(segments))


def _format_segments(segments: list) -> str:
    if not segments:
        return ""

    import re

    raw = "".join(seg.text.strip() for seg in segments if seg.text.strip())
    sents = re.split(r"(?<=[。！？])", raw)
    sents = [s.strip() for s in sents if s.strip()]

    if len(sents) <= 1:
        sents = re.split(r"(?<=[，。！？])", raw)
        sents = [s.strip() for s in sents if s.strip()]

    if len(sents) <= 1:
        sents = [raw[i:i+200] for i in range(0, len(raw), 200)]

    paragraphs = []
    buf = ""
    for s in sents:
        if not buf:
            buf = s
        elif len(buf) + len(s) < 200:
            buf += s
        else:
            paragraphs.append(buf)
            buf = s
    if buf:
        if len(buf) < 30 and paragraphs:
            paragraphs[-1] += buf
        else:
            paragraphs.append(buf)

    if len(paragraphs) > 1 and len(paragraphs[-1]) < 30:
        paragraphs[-2] += paragraphs[-1]
        paragraphs.pop()

    return "\n\n".join(paragraphs) if paragraphs else raw


def cleanup() -> None:
    if _output_dir and _output_dir.exists():
        shutil.rmtree(_output_dir, ignore_errors=True)


def transcribe_bvid(bvid: str, language: str = "zh") -> str:
    audio_path = download_audio(bvid)
    return transcribe(audio_path, language)
