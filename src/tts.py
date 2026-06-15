import asyncio
import os
import subprocess
import sys
from abc import ABC, abstractmethod
from pathlib import Path


os.environ.setdefault("AIODNS_PREFER_IPV6", "1")


class TTS(ABC):
    voice: str = ""

    @abstractmethod
    def synthesize(self, text: str, output_path: str) -> float:
        raise NotImplementedError

    @staticmethod
    def duration(path: str) -> float:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", path],
            capture_output=True, text=True,
        )
        return float(r.stdout.strip())


class EdgeTTS(TTS):
    def __init__(self, voice: str = "zh-CN-XiaoxiaoNeural"):
        self.voice = voice

    def synthesize(self, text: str, output_path: str) -> float:
        os.environ["AIODNS_PREFER_IPV6"] = "1"
        try:
            import edge_tts
        except ImportError:
            print("请先安装 edge-tts: pip install edge-tts", file=sys.stderr)
            sys.exit(1)
        asyncio.run(edge_tts.Communicate(text, self.voice).save(output_path))
        print(f"  音频已保存: {output_path}", file=sys.stderr)
        return self.duration(output_path)
