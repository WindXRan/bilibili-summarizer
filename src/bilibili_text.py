import asyncio
import re
import sys
from pathlib import Path

import requests

from .transcriber import transcribe_bvid


API_VIEW = "https://api.bilibili.com/x/web-interface/view"
API_PLAYER = "https://api.bilibili.com/x/player/v2"

TTS_VOICE = "zh-CN-XiaoxiaoNeural"
PROJECT_DIR = Path("project")

def _sanitize_filename(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "", name).strip() or "untitled"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": USER_AGENT, "Referer": "https://www.bilibili.com"})


def parse_bvid(url_or_bvid: str) -> str:
    m = re.search(r"BV\w+", url_or_bvid)
    if not m:
        raise ValueError(f"无法识别 BV 号: {url_or_bvid}")
    return m.group(0)


def get_video_info(bvid: str) -> dict:
    resp = SESSION.get(API_VIEW, params={"bvid": bvid}, timeout=15)
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"API 返回错误: {data.get('message', 'unknown')}")
    return data["data"]


def get_subtitle_list(bvid: str, cid: int) -> list[dict]:
    resp = SESSION.get(API_PLAYER, params={"bvid": bvid, "cid": cid}, timeout=15)
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"播放器 API 错误: {data.get('message', 'unknown')}")
    subtitles = data.get("data", {}).get("subtitle", {}).get("subtitles", [])
    return subtitles


def fetch_subtitle_text(subtitle_url: str) -> str:
    if subtitle_url.startswith("//"):
        subtitle_url = "https:" + subtitle_url
    resp = SESSION.get(subtitle_url, timeout=15)
    body = resp.json().get("body", [])
    lines = [seg["content"] for seg in body]
    return "\n".join(lines)


def _generate_audio(text: str, output_path: str) -> None:
    try:
        import edge_tts
    except ImportError:
        print("请先安装 edge-tts: pip install edge-tts", file=sys.stderr)
        sys.exit(1)

    asyncio.run(edge_tts.Communicate(text, TTS_VOICE).save(output_path))
    print(f"音频已保存: {output_path}", file=sys.stderr)


def _default_path(info: dict, tag: str = "") -> Path:
    owner = _sanitize_filename(info.get("owner", {}).get("name", "unknown"))
    title = _sanitize_filename(info.get("title", "untitled"))
    suffix = f"_{tag}" if tag else ""
    return PROJECT_DIR / owner / f"{title}{suffix}.txt"


def extract(bvid_or_url: str, output: str | None = None, force_asr: bool = False, tts: bool = False) -> str:
    bvid = parse_bvid(bvid_or_url)
    info = get_video_info(bvid)
    title = info.get("title", "")
    cid = info["cid"]

    auto_path = not output
    if auto_path:
        output = str(_default_path(info))

    if not force_asr:
        subtitles = get_subtitle_list(bvid, cid)
        if subtitles:
            text = fetch_subtitle_text(subtitles[0]["subtitle_url"])
            result = f"# {title}\n\n来源: API字幕 | {bvid}\n\n---\n\n{text}"
            _save(result, output, auto_path, "字幕", tts, text)
            return result
        print("无可用字幕，切换到音频识别...", file=sys.stderr)

    print("下载音频中...", file=sys.stderr)
    text = transcribe_bvid(bvid)
    result = f"# {title}\n\n来源: 音频识别 (Whisper) | {bvid}\n\n---\n\n{text}"
    _save(result, output, auto_path, "asr", tts, text)

    return result


def _save(result: str, output: str, auto_path: bool, tag: str, tts: bool, text: str) -> None:
    out = Path(output)
    if auto_path:
        out = out.with_stem(out.stem + f"_{tag}")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(result, encoding="utf-8")
    if tts:
        p = out.with_suffix(".mp3")
        _generate_audio(text, str(p))


def main():
    if len(sys.argv) < 2:
        print("用法: python -m src.bilibili_text <BV号或B站链接> [-o output.txt] [--asr] [--tts]")
        sys.exit(1)

    bvid_or_url = sys.argv[1]
    output = None
    force_asr = "--asr" in sys.argv
    do_tts = "--tts" in sys.argv
    if "-o" in sys.argv:
        idx = sys.argv.index("-o")
        if idx + 1 < len(sys.argv):
            output = sys.argv[idx + 1]

    try:
        result = extract(bvid_or_url, output, force_asr, do_tts)
        print(result)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
