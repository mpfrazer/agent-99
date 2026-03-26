#!/usr/bin/env python3
"""
start.py — launch the agent-99 web UI.

Starts FastAPI on :8000 and Next.js on :3000, then opens the browser.
Press Ctrl+C to shut both down.
"""

import platform
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).parent
WEB = ROOT / "web"
IS_WIN = platform.system() == "Windows"
PYTHON = ROOT / ".venv" / ("Scripts" if IS_WIN else "bin") / ("python.exe" if IS_WIN else "python")

FASTAPI_PORT = 8000
NEXTJS_PORT = 3000


def check_venv() -> None:
    if not PYTHON.exists():
        print("  ✗ Virtual environment not found. Run 'python install.py' first.")
        sys.exit(1)


def check_config() -> None:
    config = Path.home() / ".agent99" / "config.yaml"
    if not config.exists():
        print("  ✗ Config not found. Run 'python install.py' first.")
        sys.exit(1)


def start_fastapi() -> subprocess.Popen:
    cmd = [
        str(PYTHON), "-m", "uvicorn",
        "api.main:app",
        "--host", "0.0.0.0",
        "--port", str(FASTAPI_PORT),
        "--reload",
    ]
    print(f"  → FastAPI on http://localhost:{FASTAPI_PORT}")
    return subprocess.Popen(
        cmd,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def start_nextjs() -> subprocess.Popen:
    print(f"  → Next.js on http://localhost:{NEXTJS_PORT}")
    npm = "npm.cmd" if IS_WIN else "npm"
    return subprocess.Popen(
        [npm, "start", "--", "-p", str(NEXTJS_PORT)],
        cwd=WEB,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def wait_for_port(port: int, timeout: int = 30) -> bool:
    import socket
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection(("localhost", port), timeout=1):
                return True
        except OSError:
            time.sleep(0.5)
    return False


def stream_output(proc: subprocess.Popen, label: str) -> None:
    """Print process output with a label prefix (runs in background thread)."""
    import threading

    def _read():
        for line in proc.stdout:
            print(f"  [{label}] {line}", end="")

    t = threading.Thread(target=_read, daemon=True)
    t.start()


def main() -> None:
    print("\n\033[1;36magent-99\033[0m — starting web UI\n")
    check_venv()
    check_config()

    api_proc = start_fastapi()
    web_proc = start_nextjs()

    stream_output(api_proc, "api")
    stream_output(web_proc, "web")

    print("\n  Waiting for servers to start…")
    api_up = wait_for_port(FASTAPI_PORT)
    web_up = wait_for_port(NEXTJS_PORT)

    if not api_up:
        print("  ✗ FastAPI did not start in time")
    if not web_up:
        print("  ✗ Next.js did not start in time")

    if api_up and web_up:
        url = f"http://localhost:{NEXTJS_PORT}"
        print(f"\n  \033[32m✓ Ready at {url}\033[0m\n")
        time.sleep(1)
        webbrowser.open(url)

    print("  Press Ctrl+C to stop.\n")

    try:
        while True:
            # Exit if either process dies unexpectedly
            if api_proc.poll() is not None:
                print("  ✗ FastAPI exited unexpectedly")
                break
            if web_proc.poll() is not None:
                print("  ✗ Next.js exited unexpectedly")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n  Shutting down…")
    finally:
        for proc in (api_proc, web_proc):
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
        print("  Done.\n")


if __name__ == "__main__":
    main()
