import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from src.tts import EdgeTTS

_tts = EdgeTTS()
OUT_W = 1920
OUT_H = 1080
FPS = 30

HTML_TPL = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
*{{margin:0;padding:0}}
body{{width:{w}px;height:{h}px;background:#000;display:flex;
justify-content:center;align-items:center;
font-family:"Microsoft YaHei","PingFang SC",sans-serif;overflow:hidden}}
.t{{color:#fff;font-size:{fs}px;text-align:center;line-height:1.8;padding:60px;max-width:85%}}
</style></head><body><div class="t">{text}</div></body></html>"""


def _split_slides(text: str, sentence_mode: bool = False) -> list[str]:
    if sentence_mode:
        slides = [l.strip() for l in text.strip().split("\n") if l.strip()]
    else:
        slides = [p.strip() for p in text.strip().split("\n\n") if p.strip()]
    return slides if slides else [text.strip()]


def _font_size(text_len: int) -> int:
    return max(32, min(60, 60 - text_len // 20))


def _gen_html(slides: list[str], out_dir: Path) -> list[Path]:
    paths = []
    for i, text in enumerate(slides):
        fs = _font_size(len(text))
        html = HTML_TPL.format(w=OUT_W, h=OUT_H, fs=fs, text=text.replace("\n", "<br>"))
        p = out_dir / f"slide_{i:04d}.html"
        p.write_text(html, encoding="utf-8")
        paths.append(p)
    return paths


def _gen_audio(text: str, out_path: Path) -> float:
    return _tts.synthesize(text, str(out_path))


def _screenshot(html_paths: list[Path], out_dir: Path) -> list[Path]:
    from playwright.sync_api import sync_playwright

    img_paths = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": OUT_W, "height": OUT_H})
        for i, hp in enumerate(html_paths):
            page.goto(hp.absolute().as_uri(), wait_until="networkidle")
            img = out_dir / f"slide_{i:04d}.png"
            page.screenshot(path=str(img), full_page=False)
            img_paths.append(img)
        browser.close()
    return img_paths


def _make_video(
    img_dir: Path, img_pattern: str, audio_path: Path,
    durations: list[float], output: Path,
):
    t = tempfile.mktemp(suffix=".txt")
    try:
        with open(t, "w", encoding="utf-8") as f:
            for i, d in enumerate(durations):
                f.write(f"file '{img_dir / img_pattern.replace('*', f'{i:04d}')}'\n")
                f.write(f"duration {d:.3f}\n")
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", t,
            "-i", str(audio_path),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest",
            str(output),
        ]
        subprocess.run(cmd, capture_output=True, check=True)
    finally:
        Path(t).unlink(missing_ok=True)


def render(input_file: str, output: str | None = None, voice: str | None = None, sentence_mode: bool = False):
    text = Path(input_file).read_text(encoding="utf-8")
    lines = text.split("\n")
    content_lines = [l for l in lines if not l.startswith("#") and not l.startswith("来源") and not l.startswith("---")]
    clean = "\n".join(content_lines).strip()

    if not clean:
        print("错误: 输入文件为空", file=sys.stderr)
        sys.exit(1)

    if voice:
        _tts.voice = voice

    out_name = output or (Path(input_file).with_suffix(".mp4"))
    out_path = Path(out_name)
    tmp = Path(tempfile.mkdtemp(prefix="render_"))

    print("1/5 切分幻灯片...", file=sys.stderr)
    slides = _split_slides(clean, sentence_mode)
    print(f"  共 {len(slides)} 页", file=sys.stderr)

    print("2/5 生成HTML + 截图...", file=sys.stderr)
    html_paths = _gen_html(slides, tmp)
    img_paths = _screenshot(html_paths, tmp)

    print("3/5 生成配音...", file=sys.stderr)
    full_audio = tmp / "audio_full.mp3"
    total_dur = _gen_audio(clean, full_audio)
    print(f"  音频 {total_dur:.1f}s", file=sys.stderr)

    total_chars = sum(len(s) for s in slides)
    durations = [max(1.2, len(s) / total_chars * total_dur) for s in slides]
    # smooth: don't let adjacent slides differ by more than 2x
    for i in range(1, len(durations)):
        if durations[i] > durations[i-1] * 2:
            durations[i] = durations[i-1] * 2
        if durations[i-1] > durations[i] * 2:
            durations[i-1] = durations[i] * 2

    print("5/5 合成视频...", file=sys.stderr)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _make_video(tmp, "slide_*.png", full_audio, durations, out_path)

    shutil.rmtree(tmp, ignore_errors=True)
    print(f"完成: {out_path}", file=sys.stderr)


def main():
    if len(sys.argv) < 2:
        print("用法: python render.py <input.txt> [-o output.mp4] [--voice VOICE] [--sentences]")
        sys.exit(1)

    input_file = sys.argv[1]
    output = None
    voice = None
    sentence_mode = "--sentences" in sys.argv
    if "-o" in sys.argv:
        idx = sys.argv.index("-o")
        if idx + 1 < len(sys.argv):
            output = sys.argv[idx + 1]
    if "--voice" in sys.argv:
        idx = sys.argv.index("--voice")
        if idx + 1 < len(sys.argv):
            voice = sys.argv[idx + 1]

    render(input_file, output, voice, sentence_mode)


if __name__ == "__main__":
    main()
