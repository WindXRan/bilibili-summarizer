import hashlib
import json
import random
import re
import sys
import time
import urllib.parse
from pathlib import Path

import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com",
}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)
_COOKIE_FILE = Path(__file__).resolve().parent / "bilibili_cookies.txt"


def _load_cookies():
    if _COOKIE_FILE.exists():
        txt = _COOKIE_FILE.read_text(encoding="utf-8").strip()
        if txt and txt not in SESSION.headers.get("Cookie", ""):
            SESSION.headers.update({"Cookie": txt})
            print(f"  已加载Cookie: {txt[:30]}...", file=sys.stderr)

_WBI_CACHE = {}


def _wbi_keys():
    if "keys" in _WBI_CACHE:
        return _WBI_CACHE["keys"]
    r = SESSION.get("https://api.bilibili.com/x/web-interface/nav", timeout=15)
    d = r.json()
    img = d.get("data", {}).get("wbi_img", {}).get("img_url", "")
    sub = d.get("data", {}).get("wbi_img", {}).get("sub_url", "")
    if img and sub:
        ik = img.rsplit("/", 1)[1].split(".")[0]
        sk = sub.rsplit("/", 1)[1].split(".")[0]
        _WBI_CACHE["keys"] = (ik, sk)
        return ik, sk
    raise RuntimeError("无法获取 WBI keys")


def _sign(params):
    ik, sk = _wbi_keys()
    mix = sk[:4] + ik[:4]
    p = {str(k): str(v) for k, v in params.items()}
    p["wts"] = str(int(time.time()))
    q = urllib.parse.urlencode(sorted(p.items()))
    p["w_rid"] = hashlib.md5((q + mix).encode()).hexdigest()
    return p


def _api(url, params, retries=10):
    for i in range(retries):
        signed = _sign(params)
        try:
            r = SESSION.get(url, params=signed, timeout=15)
        except requests.exceptions.ConnectionError as e:
            print(f"  连接失败，等待重试 {i+1}/{retries}: {e}", file=sys.stderr)
            time.sleep(min(10 * (2**i), 60))
            _WBI_CACHE.pop("keys", None)
            continue
        try:
            d = r.json()
        except Exception:
            d = {"code": -1}
        if d.get("code") == 0:
            return d
        msg = d.get("message", "")
        if d.get("code") == -799:
            t = min(30 * (2**i), 300)
            print(f"  限频，等待 {t}s...", file=sys.stderr)
            time.sleep(t)
        elif d.get("code") == -352:
            _WBI_CACHE.pop("keys", None)
            print(f"  签名过期，重试 {i+1}/{retries}", file=sys.stderr)
            time.sleep(2)
        else:
            print(f"  API错误: {msg}", file=sys.stderr)
            return d if d.get("code") != -1 else None
    return None


def get_mid(bvid_or_url):
    m = re.search(r"BV\w+", bvid_or_url)
    if m:
        d = _api("https://api.bilibili.com/x/web-interface/view", {"bvid": m.group(0)})
        return d["data"]["owner"]["mid"]
    m = re.search(r"space\.bilibili\.com/(\d+)", bvid_or_url)
    if m:
        return int(m.group(1))
    s = bvid_or_url.strip()
    if s.isdigit():
        return int(s)
    raise ValueError(f"无法解析: {bvid_or_url}")


def get_up_name(mid):
    d = _api("https://api.bilibili.com/x/web-interface/card", {"mid": mid})
    return d.get("data", {}).get("card", {}).get("name", str(mid))


def init(cookie: str = ""):
    if cookie:
        SESSION.headers.update({"Cookie": cookie.strip()})
    else:
        _load_cookies()


def get_all_bvs(mid):
    d = _api("https://api.bilibili.com/x/space/arc/search", {"mid": mid, "ps": "30", "pn": "1"})
    if not d:
        return []
    page = d.get("data", {}).get("page", {})
    total = page.get("count", 0)
    pages = (total + 29) // 30 if total else 1
    vlist = d.get("data", {}).get("list", {}).get("vlist", [])
    bvs = [{"bvid": v["bvid"], "title": v["title"]} for v in vlist]
    print(f"  第1页: {len(vlist)}个 (共{total}个)", file=sys.stderr)
    for pn in range(2, pages + 1):
        d = _api("https://api.bilibili.com/x/space/arc/search", {"mid": mid, "ps": "30", "pn": str(pn)})
        if not d:
            break
        vlist = d.get("data", {}).get("list", {}).get("vlist", [])
        bvs.extend({"bvid": v["bvid"], "title": v["title"]} for v in vlist)
        print(f"  第{pn}页: {len(vlist)}个", file=sys.stderr)
        if len(vlist) < 30:
            break
        time.sleep(random.uniform(3, 6))
    return bvs


def main():
    if len(sys.argv) < 2:
        print("用法: python -m src.up_bvs <BV号|UP主mid|space链接> [--cookie \"xxx\"]")
        sys.exit(1)

    cookie = ""
    args = sys.argv[1:]
    if "--cookie" in args:
        idx = args.index("--cookie")
        cookie = args[idx + 1]
        args = args[:idx]
    init(cookie)

    mid = get_mid(args[0])
    name = get_up_name(mid)
    print(f"UP主: {name} (mid={mid})", file=sys.stderr)
    bvs = get_all_bvs(mid)
    for v in bvs:
        print(f"{v['bvid']} | {v['title']}")
    print(f"共 {len(bvs)} 个视频", file=sys.stderr)


if __name__ == "__main__":
    main()
