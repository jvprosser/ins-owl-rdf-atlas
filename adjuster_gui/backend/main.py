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
import signal
import socket
import subprocess
import sys
import threading
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


def _bind_host(host: str) -> str:
    return "0.0.0.0" if host in ("", "0.0.0.0") else host


def _port_in_use(host: str, port: int) -> bool:
    """True when uvicorn would fail to bind. A connect to 127.0.0.1 can miss that."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((_bind_host(host), port))
    except OSError:
        return True
    finally:
        sock.close()
    return False


def _listen_inodes(port: int) -> set[str]:
    inodes: set[str] = set()
    port_hex = f"{port:04X}"
    for path in ("/proc/net/tcp", "/proc/net/tcp6"):
        try:
            with open(path, encoding="utf-8") as fh:
                lines = fh.read().splitlines()[1:]
        except OSError:
            continue
        for line in lines:
            parts = line.split()
            if len(parts) < 10:
                continue
            local_port = parts[1].rsplit(":", 1)[-1].upper()
            if local_port == port_hex and parts[3] == "0A":
                inodes.add(parts[9])
    return inodes


def _pids_listening_on(port: int) -> list[int]:
    inodes = _listen_inodes(port)
    if not inodes or not os.path.isdir("/proc"):
        return []
    found: list[int] = []
    for name in os.listdir("/proc"):
        if not name.isdigit():
            continue
        fd_dir = os.path.join("/proc", name, "fd")
        try:
            fds = os.listdir(fd_dir)
        except OSError:
            continue
        for fd in fds:
            try:
                target = os.readlink(os.path.join(fd_dir, fd))
            except OSError:
                continue
            if target.startswith("socket:[") and target[8:-1] in inodes:
                found.append(int(name))
                break
    return found


def _cmdline(pid: int) -> str:
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as fh:
            raw = fh.read()
    except OSError:
        return ""
    return raw.replace(b"\x00", b" ").decode(errors="replace").strip()


def _holders(port: int) -> list[str]:
    described = [
        f"{pid} {_cmdline(pid)}".strip() for pid in _pids_listening_on(port)
    ]
    return described or ["unidentified process"]


def _engine_only(port: int) -> bool:
    """True when the Cloudera editor, not another app, owns the port."""
    pids = _pids_listening_on(port)
    if not pids:
        return False
    for pid in pids:
        cmd = _cmdline(pid)
        if "app.main:app" in cmd:
            return False
        if pid != 1 and "jupyter-wsg-launcher" not in cmd and "engine-init" not in cmd:
            return False
    return True


def _ensure_port_free(host: str, port: int) -> None:
    """Stop a leftover adjuster uvicorn so a re-run can bind the port."""
    if not _port_in_use(host, port):
        return
    if _engine_only(port):
        raise RuntimeError(
            f"Port {port} is used by the Cloudera editor ({'; '.join(_holders(port))})."
        )
    ours = [pid for pid in _pids_listening_on(port) if "app.main:app" in _cmdline(pid)]
    for pid in ours:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
    if ours and _wait_port_free(host, port, _PORT_FREE_TIMEOUT_S):
        print(f"Stopped leftover adjuster server on port {port}.")
        return
    if not _port_in_use(host, port):
        return
    raise RuntimeError(
        f"Port {port} is already in use ({'; '.join(_holders(port))}). "
        "Stop that process or restart the CML engine."
    )


def _choose_port(host: str, port: int) -> int:
    """Use CDSW_APP_PORT unless the session editor already bound it.

    Jupyter in a Cloudera session listens on CDSW_APP_PORT. The other exposed
    port is CDSW_READONLY_PORT (https://read-only-<engine>.<domain>). An
    Application engine does not run that editor, so CDSW_APP_PORT stays free.
    """
    if not _port_in_use(host, port):
        return port
    if not _engine_only(port):
        _ensure_port_free(host, port)
        return port
    readonly = os.environ.get("CDSW_READONLY_PORT")
    if not readonly:
        raise RuntimeError(
            f"Port {port} is used by the Cloudera editor ({'; '.join(_holders(port))}). "
            "Create an Application so CDSW_APP_PORT is free, or set CDSW_READONLY_PORT."
        )
    alt = int(readonly)
    if _port_in_use(host, alt):
        _ensure_port_free(host, alt)
    engine = os.environ.get("CDSW_ENGINE_ID", "<engine>")
    domain = os.environ.get("CDSW_DOMAIN", "<domain>")
    print(
        f"Port {port} is used by the Cloudera editor. "
        f"Serving on CDSW_READONLY_PORT {alt} "
        f"(https://read-only-{engine}.{domain})."
    )
    return alt


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
    _wait_port_free(app_main.APP_HOST, app_main.APP_PORT, 2.0)


def _package_backend_dir() -> str:
    """Directory that contains the app package actually imported in this kernel."""
    return os.path.dirname(os.path.dirname(os.path.abspath(app_main.__file__)))


def _child_env(backend_dir: str, port: int) -> dict[str, str]:
    env = os.environ.copy()
    prior = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = backend_dir if not prior else backend_dir + os.pathsep + prior
    # The child reads CDSW_APP_PORT when it imports app.main.
    env["CDSW_APP_PORT"] = str(port)
    return env


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


def _pump_output(proc: subprocess.Popen[str], lines: list[str]) -> None:
    if proc.stdout is None:
        return
    for line in proc.stdout:
        lines.append(line)
        sys.stderr.write(line)
        sys.stderr.flush()


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

    _stop_existing()
    app_main.APP_PORT = _choose_port(app_main.APP_HOST, app_main.APP_PORT)

    backend_dir = _package_backend_dir()
    print(
        f"Starting uvicorn from {backend_dir} "
        f"on {app_main.APP_HOST}:{app_main.APP_PORT}"
    )
    proc = subprocess.Popen(
        _uvicorn_cmd(),
        cwd=backend_dir,
        env=_child_env(backend_dir, app_main.APP_PORT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    app_main._server_proc = proc
    output: list[str] = []
    pump = threading.Thread(target=_pump_output, args=(proc, output), daemon=True)
    pump.start()

    deadline = time.time() + _STARTUP_TIMEOUT_S
    while time.time() < deadline:
        code = proc.poll()
        if code is not None:
            pump.join(timeout=2)
            detail = "".join(output).strip() or "(no output)"
            raise RuntimeError(
                f"Uvicorn exited during startup (code {code}) "
                f"from {backend_dir} on port {app_main.APP_PORT}.\n{detail}"
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
