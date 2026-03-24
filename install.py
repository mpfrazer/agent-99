#!/usr/bin/env python3
"""
install.py — one-shot setup for agent-99.

Works on Linux, macOS, and Windows.
Run with: python install.py
"""

import getpass
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
VENV = ROOT / ".venv"
WEB = ROOT / "web"
CONFIG_DIR = Path.home() / ".agent99"
CONFIG_FILE = CONFIG_DIR / "config.yaml"

IS_WIN = platform.system() == "Windows"
PYTHON = VENV / ("Scripts" if IS_WIN else "bin") / ("python.exe" if IS_WIN else "python")


def banner(msg: str) -> None:
    print(f"\n\033[1;36m{'─' * 60}\n  {msg}\n{'─' * 60}\033[0m")


def run(cmd: list, **kwargs) -> None:
    print(f"  $ {' '.join(str(c) for c in cmd)}")
    subprocess.run(cmd, check=True, **kwargs)


def check_python() -> None:
    banner("Checking Python version")
    v = sys.version_info
    if v < (3, 11):
        print(f"\033[31m  ✗ Python 3.11+ required (found {v.major}.{v.minor})\033[0m")
        sys.exit(1)
    print(f"  ✓ Python {v.major}.{v.minor}.{v.micro}")


def check_node() -> None:
    banner("Checking Node.js version")
    node = shutil.which("node")
    if not node:
        print("\033[31m  ✗ Node.js not found. Install Node 18+ from https://nodejs.org\033[0m")
        sys.exit(1)
    result = subprocess.run(["node", "--version"], capture_output=True, text=True)
    version_str = result.stdout.strip().lstrip("v")
    major = int(version_str.split(".")[0])
    if major < 18:
        print(f"\033[31m  ✗ Node 18+ required (found {result.stdout.strip()})\033[0m")
        sys.exit(1)
    print(f"  ✓ Node.js {result.stdout.strip()}")


def create_venv() -> None:
    banner("Creating Python virtual environment")
    if VENV.exists():
        print("  ↩  .venv already exists, skipping")
        return
    run([sys.executable, "-m", "venv", str(VENV)])
    # Ensure pip is available (Ubuntu omits it when ensurepip is missing)
    if not (VENV / ("Scripts" if IS_WIN else "bin") / ("pip.exe" if IS_WIN else "pip")).exists():
        run([str(PYTHON), "-m", "ensurepip", "--upgrade"])
    print("  ✓ Created .venv")


def install_python_deps() -> None:
    banner("Installing Python dependencies")
    run([str(PYTHON), "-m", "pip", "install", "--upgrade", "pip", "--quiet"])
    run([str(PYTHON), "-m", "pip", "install", "-e", ".[web]", "--quiet"])
    print("  ✓ Python dependencies installed")


def install_node_deps() -> None:
    banner("Installing Node.js dependencies")
    run(["npm", "install", "--legacy-peer-deps"], cwd=WEB)
    print("  ✓ Node dependencies installed")


def build_frontend() -> None:
    banner("Building Next.js frontend")
    run(["npm", "run", "build"], cwd=WEB)
    print("  ✓ Frontend built")


def setup_config() -> None:
    banner("Setting up ~/.agent99 configuration")
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    (CONFIG_DIR / "runs").mkdir(exist_ok=True)

    if CONFIG_FILE.exists():
        print("  ↩  Config already exists, skipping password setup")
        return

    import secrets
    import yaml

    # Bootstrap config without password
    cfg = {
        "password_hash": None,
        "secret_key": secrets.token_hex(32),
        "runs_dir": str(CONFIG_DIR / "runs"),
    }
    CONFIG_FILE.write_text(yaml.safe_dump(cfg))

    # Prompt for password
    print("\n  Set a password for the web UI:")
    while True:
        pw = getpass.getpass("  Password: ")
        pw2 = getpass.getpass("  Confirm:  ")
        if not pw:
            print("  Password must not be empty.")
            continue
        if pw != pw2:
            print("  Passwords do not match, try again.")
            continue
        break

    # Hash and save
    import bcrypt
    cfg["password_hash"] = bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
    CONFIG_FILE.write_text(yaml.safe_dump(cfg))
    print("  ✓ Password saved to ~/.agent99/config.yaml")


def done() -> None:
    banner("Installation complete!")
    print("  Start the app with:")
    print("    python start.py\n")
    print("  Then open http://localhost:3000 in your browser.\n")


if __name__ == "__main__":
    try:
        check_python()
        check_node()
        create_venv()
        install_python_deps()
        install_node_deps()
        build_frontend()
        setup_config()
        done()
    except subprocess.CalledProcessError as e:
        print(f"\n\033[31m  ✗ Command failed (exit {e.returncode})\033[0m")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n  Cancelled.")
        sys.exit(1)
