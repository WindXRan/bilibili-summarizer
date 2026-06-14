import os
import shutil
import subprocess
import sys
import tempfile
import re
from pathlib import Path

import httpx

API_VIEW = "https://api.bilibili.com/x/web-interface/view"
API_PLAYURL = "https://api.bilibili.com/x/player/playurl"

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.bilibili.com",
}

_output_dir: Path | None = None


def get_output_dir() -> Path:
    global _output_dir
    if _output_dir is None:
        _output_dir = Path(tempfile.mkdtemp(prefix="bili_ocr_"))
    _output_dir.mkdir(parents=True, exist_ok=True)
    return _output_dir


def download_video(bvid: str) -> Path:
    out = get_output_dir()
    video_path = out / f"{bvid}.mp4"
    if video_path.exists():
        return video_path

    raw_path = out / f"{bvid}.m4s"

    with httpx.Client(headers=_HEADERS, follow_redirects=True, timeout=30, verify=False) as c:
        info = c.get(API_VIEW, params={"bvid": bvid}).json()
        if info.get("code") != 0:
            raise RuntimeError(f"获取视频信息失败: {info.get('message')}")
        cid = info["data"]["cid"]

        play = c.get(API_PLAYURL, params={"bvid": bvid, "cid": cid, "fnval": 4048}).json()
        if play.get("code") != 0:
            raise RuntimeError(f"获取视频链接失败: {play.get('message')}")

        video_streams = play["data"]["dash"]["video"]
        video_url = video_streams[0]["baseUrl"]

        resp = c.get(video_url, timeout=300)
        resp.raise_for_status()
        raw_path.write_bytes(resp.content)

    subprocess.run(
        ["ffmpeg", "-y", "-i", str(raw_path), "-c", "copy", str(video_path)],
        capture_output=True, check=True,
    )
    raw_path.unlink(missing_ok=True)
    return video_path


def extract_frames(video_path: Path, interval: int = 5) -> list[Path]:
    out = get_output_dir() / "frames"
    out.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(video_path),
            "-vf", f"fps=1/{interval}",
            "-q:v", "2",
            str(out / "frame_%04d.jpg"),
        ],
        capture_output=True, check=True,
    )

    frames = sorted(out.glob("frame_*.jpg"))
    return frames


def ocr_frame(image_path: Path) -> str:
    try:
        import easyocr
    except ImportError:
        print("请先安装 easyocr: pip install easyocr", file=sys.stderr)
        sys.exit(1)

    reader = easyocr.Reader(["ch_sim", "en"], gpu=False)
    results = reader.readtext(str(image_path))
    texts = [r[1] for r in results]
    return "\n".join(texts)


def ocr_video(bvid_or_url: str, interval: int = 5) -> str:
    m = re.search(r"BV\w+", bvid_or_url)
    if not m:
        raise ValueError(f"无法识别 BV 号: {bvid_or_url}")
    bvid = m.group(0)

    with httpx.Client(headers=_HEADERS, follow_redirects=True, timeout=30, verify=False) as c:
        info = c.get(API_VIEW, params={"bvid": bvid}).json()
        title = info.get("data", {}).get("title", "")

    print(f"正在下载视频 {bvid}...", file=sys.stderr)
    video_path = download_video(bvid)

    print(f"正在抽帧 (每{interval}秒一帧)...", file=sys.stderr)
    frames = extract_frames(video_path, interval)
    print(f"共 {len(frames)} 帧", file=sys.stderr)

    print("正在 OCR 识别...", file=sys.stderr)
    all_text = []
    seen = set()
    for i, frame_path in enumerate(frames):
        print(f"  [{i+1}/{len(frames)}] {frame_path.name}", file=sys.stderr)
        text = ocr_frame(frame_path)
        for line in text.split("\n"):
            line = line.strip()
            if line and line not in seen:
                all_text.append(line)
                seen.add(line)

    result = f"# {title}\n\n来源: 截图OCR | {bvid}\n\n---\n\n" + "\n".join(all_text)
    return result


def main():
    if len(sys.argv) < 2:
        print("用法: python -m src.ocr <BV号或B站链接> [-o output.txt]")
        sys.exit(1)

    bvid_or_url = sys.argv[1]
    output = None
    if "-o" in sys.argv:
        idx = sys.argv.index("-o")
        if idx + 1 < len(sys.argv):
            output = sys.argv[idx + 1]

    try:
        result = ocr_video(bvid_or_url)
        if output:
            Path(output).write_text(result, encoding="utf-8")
        print(result)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


def cleanup() -> None:
    global _output_dir
    if _output_dir and _output_dir.exists():
        shutil.rmtree(_output_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
