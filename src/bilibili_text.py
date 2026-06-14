import json
import re
import sys
from pathlib import Path

import requests


API_VIEW = "https://api.bilibili.com/x/web-interface/view"
API_PLAYER = "https://api.bilibili.com/x/player/v2"

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


def extract(bvid_or_url: str, output: str | None = None) -> str:
    bvid = parse_bvid(bvid_or_url)
    info = get_video_info(bvid)
    title = info.get("title", "")
    cid = info["cid"]

    subtitles = get_subtitle_list(bvid, cid)
    if not subtitles:
        return f"视频「{title}」没有可用的字幕"

    text = fetch_subtitle_text(subtitles[0]["subtitle_url"])
    result = f"# {title}\n\n{bvid}\n\n---\n\n{text}"

    if output:
        Path(output).write_text(result, encoding="utf-8")

    return result


def main():
    if len(sys.argv) < 2:
        print("用法: python -m src.bilibili_text <BV号或B站链接> [-o output.txt]")
        sys.exit(1)

    bvid_or_url = sys.argv[1]
    output = None
    if "-o" in sys.argv:
        idx = sys.argv.index("-o")
        if idx + 1 < len(sys.argv):
            output = sys.argv[idx + 1]

    try:
        result = extract(bvid_or_url, output)
        print(result)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
