"""Chụp màn hình viewer bằng Edge/Chrome headless (không cần Playwright).

    python scripts/screenshot_viewer.py results/<run>/eval/pid/traj_9000.json docs/screenshots/x.png [--frame 120]
"""
from __future__ import annotations

import argparse
import functools
import http.server
import os
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BROWSERS = [  # Chrome trước: msedge.exe gọi từ subprocess thoát ngay (bàn giao cho tiến trình Edge đang chạy) nên không chụp được
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve(port: int):
    handler = functools.partial(_Quiet, directory=str(ROOT))
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", port), handler)
    httpd.daemon_threads = True
    th = threading.Thread(target=httpd.serve_forever, daemon=True)
    th.start()
    return httpd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("traj")
    ap.add_argument("out")
    ap.add_argument("--frame", type=int, default=None)
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--wait", type=int, default=12000)
    args = ap.parse_args()
    browser = next((b for b in BROWSERS if Path(b).exists()), None)
    if not browser:
        print("không thấy Edge/Chrome", file=sys.stderr)
        sys.exit(1)
    rel = Path(args.traj).resolve().relative_to(ROOT).as_posix()
    url = f"http://127.0.0.1:{args.port}/viewer/index.html?file=/{rel}"
    if args.frame is not None:
        url += f"&frame={args.frame}"
    httpd = serve(args.port)
    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    prof = tempfile.mkdtemp(prefix="viewer_prof_")
    try:
        cmd = [browser, "--headless=new", "--disable-gpu", "--no-first-run", "--hide-scrollbars", f"--user-data-dir={prof}",
               "--window-size=1400,860", f"--virtual-time-budget={args.wait}", f"--screenshot={out}", url]
        t0 = time.time()
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        ok = out.exists() and out.stat().st_size > 1000
        print(f"{'OK' if ok else 'FAIL'} {out} ({out.stat().st_size if out.exists() else 0} bytes, {time.time()-t0:.1f}s) url={url}")
        if not ok:
            print(r.stdout[-2000:], r.stderr[-2000:])
            sys.exit(1)
    finally:
        httpd.shutdown()
        shutil.rmtree(prof, ignore_errors=True)


if __name__ == "__main__":
    main()
