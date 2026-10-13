"""Process entrypoint. `python adjuster_gui/backend/main.py` (CML Application command).

Binds CDSW_APP_PORT when running as a Cloudera AI Application; 8010 locally.

Cloudera AI Applications execute this script inside a notebook kernel. Starting
uvicorn in that kernel hits asyncio event-loop conflicts, so uvicorn runs as a
child process — the same pattern as the Process Mapper.

Re-running the entrypoint must not bind the port twice. If this server is already
healthy, the re-run attaches to the existing subprocess.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

try:
    _BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _cwd = os.getcwd()
    _candidates = [
        _cwd if os.path.basename(_cwd) == "backend" else "",
        os.path.join(_cwd, "adjuster_gui", "backend"),
        os.path.join(_cwd, "backend"),
    ]
    _BACKEND_DIR = next(
        (
            path
            for path in _candidates
            if path and os.path.isfile(os.path.join(path, "main.py"))
        ),
        os.path.join(_cwd, "adjuster_gui", "backend"),
    )
BACKEND_DIR = os.environ.get("BACKEND_DIR", _BACKEND_DIR)

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import main as app_main  # noqa: E402

_SHUTDOWN_TIMEOUT_S = 30.0
_PORT_FREE_TIMEOUT_S = 20.0
_STARTUP_TIMEOUT_S = 15.0


def _probe_host(host: str) -> str:
    return "127.0.0.1" if host in ("", "0.0.0.0") else host


def _health_ok(host: str, port: int) -> bool:
    url = f"http://{_probe_host(host)}:{port}/health"
    try:
        with urllib.request.urlopen(url, timeout=2) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def _port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex((_probe_host(host), port)) == 0


def _wait_port_free(host: str, port: int, timeout: float) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not _port_in_use(host, port):
            return True
        time.sleep(0.25)
    return False


def _proc_alive() -> bool:
    proc = app_main._server_proc
    return proc is not None and proc.poll() is None


def _already_running() -> bool:
    return _proc_alive() and _health_ok(app_main.APP_HOST, app_main.APP_PORT)


def _stop_existing() -> None:
    proc = app_main._server_proc
    if proc is not None and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=_SHUTDOWN_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
    app_main._server_proc = None
    if not _wait_port_free(app_main.APP_HOST, app_main.APP_PORT, _PORT_FREE_TIMEOUT_S):
        raise RuntimeError(
            f"Port {app_main.APP_PORT} is still in use after shutdown. "
            "Restart the CML kernel, or stop the other Application using this port."
        )


def _uvicorn_cmd() -> list[str]:
    return [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        app_main.APP_HOST,
        "--port",
        str(app_main.APP_PORT),
        "--log-level",
        "info",
    ]


def run() -> None:
    """Spawn uvicorn in a subprocess and block until it exits."""
    if _already_running():
        print(
            f"Adjuster GUI already serving on port {app_main.APP_PORT} "
            "(re-run attaches to the running server; no restart)."
        )
        try:
            app_main._server_proc.wait()
        except KeyboardInterrupt:
            _stop_existing()
        return

    if _port_in_use(app_main.APP_HOST, app_main.APP_PORT) and not _health_ok(
        app_main.APP_HOST, app_main.APP_PORT
    ):
        raise RuntimeError(
            f"Port {app_main.APP_PORT} is in use but is not our /health endpoint. "
            "Restart the CML kernel or free the port before starting."
        )

    _stop_existing()

    proc = subprocess.Popen(
        _uvicorn_cmd(),
        cwd=BACKEND_DIR,
        env=os.environ.copy(),
    )
    app_main._server_proc = proc

    deadline = time.time() + _STARTUP_TIMEOUT_S
    while time.time() < deadline:
        code = proc.poll()
        if code is not None:
            raise RuntimeError(
                f"Uvicorn exited during startup (code {code}). "
                "Check stderr above for bind errors (e.g. address already in use)."
            )
        if _health_ok(app_main.APP_HOST, app_main.APP_PORT):
            print(f"Adjuster GUI serving on port {app_main.APP_PORT} (pid {proc.pid})")
            break
        time.sleep(0.2)
    else:
        _stop_existing()
        raise RuntimeError(
            f"Uvicorn started (pid {proc.pid}) but /health did not respond "
            f"within {_STARTUP_TIMEOUT_S:.0f}s on port {app_main.APP_PORT}."
        )

    try:
        proc.wait()
    except KeyboardInterrupt:
        _stop_existing()


if __name__ == "__main__":
    run()
