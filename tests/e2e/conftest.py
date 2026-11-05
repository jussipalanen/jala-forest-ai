"""Start a real Streamlit server with synthetic data for the Playwright tests."""

import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest
from synthetic import write_synthetic_stands

ROOT = Path(__file__).resolve().parents[2]


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _start(data_path: Path, ai_enabled: bool):
    port = _free_port()
    env = os.environ | {"DATA_PATH": str(data_path), "AI_ENABLED": "true" if ai_enabled else "false"}
    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app/streamlit_app.py",
         "--server.headless", "true", "--server.port", str(port), "--server.address", "127.0.0.1"],
        cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
    )
    url = f"http://127.0.0.1:{port}"
    for _ in range(60):
        try:
            with urllib.request.urlopen(f"{url}/_stcore/health", timeout=1) as r:
                if r.status == 200:
                    return proc, url
        except OSError:
            time.sleep(0.5)
    proc.kill()
    raise RuntimeError("Streamlit did not start")


@pytest.fixture(scope="session")
def data_file(tmp_path_factory):
    return write_synthetic_stands(tmp_path_factory.mktemp("data") / "stands.parquet")


@pytest.fixture(scope="session")
def app_url(data_file):
    proc, url = _start(data_file, ai_enabled=True)
    yield url
    proc.terminate()
    proc.wait(10)


@pytest.fixture(scope="session")
def app_url_ai_off(data_file):
    proc, url = _start(data_file, ai_enabled=False)
    yield url
    proc.terminate()
    proc.wait(10)
