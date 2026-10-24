"""Minimal raw socket client for Herdr's newline-delimited JSON API on Windows named pipes.

Herdr maps a session socket path to the pipe name ``\\\\.\\pipe\\<path>`` (src/platform/windows.rs:36).
Requests are one JSON object per line; a response line echoes the request ``id`` (docs/socket-api "Socket transport").
``events.subscribe`` keeps the connection open and pushes event lines after the acknowledgement.

This client is for research tests only. It never discovers sockets from the user's environment; the caller
must pass the socket path reported by the isolated server (``herdr session list --json``).
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Callable, Iterable


def pipe_name_for(socket_path: str | Path) -> str:
    text = str(socket_path)
    if text.startswith(r"\\.\pipe\\") or text.startswith(r"\\.\pipe\\".replace("\\\\", "\\")):
        return text
    return r"\\.\pipe" + "\\" + text


class HerdrPipeConnection:
    def __init__(self, socket_path: str | Path, connect_timeout: float = 10.0):
        self.pipe_name = pipe_name_for(socket_path)
        deadline = time.monotonic() + connect_timeout
        last_error: OSError | None = None
        while True:
            try:
                # Opening the pipe as an unbuffered binary file gives a duplex byte stream on Windows.
                self._handle = open(self.pipe_name, "r+b", buffering=0)
                break
            except OSError as err:  # pipe busy / not yet listening
                last_error = err
                if time.monotonic() > deadline:
                    raise
                time.sleep(0.05)
        self._buffer = b""
        self._lock = threading.Lock()

    def close(self) -> None:
        try:
            self._handle.close()
        except OSError:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def send(self, obj: dict) -> None:
        payload = (json.dumps(obj, separators=(",", ":")) + "\n").encode("utf-8")
        with self._lock:
            self._handle.write(payload)
            self._handle.flush()

    def read_line(self, timeout: float | None = None) -> dict | None:
        """Read one JSON line. Blocking; timeout is best-effort via a watchdog that closes the pipe."""
        timer = None
        if timeout is not None:
            timer = threading.Timer(timeout, self.close)
            timer.daemon = True
            timer.start()
        try:
            while b"\n" not in self._buffer:
                try:
                    chunk = self._handle.read(65536)
                except (OSError, ValueError):
                    chunk = b""
                if not chunk:
                    if self._buffer.strip():
                        line, self._buffer = self._buffer, b""
                        return json.loads(line.decode("utf-8"))
                    return None
                self._buffer += chunk
            line, _, self._buffer = self._buffer.partition(b"\n")
            return json.loads(line.decode("utf-8"))
        finally:
            if timer is not None:
                timer.cancel()


def request(socket_path: str | Path, method: str, params: dict | None = None, timeout: float = 30.0) -> dict:
    """One request/response exchange on a fresh connection, like the CLI does."""
    req_id = f"research:{method}:{uuid.uuid4().hex[:8]}"
    with HerdrPipeConnection(socket_path) as conn:
        conn.send({"id": req_id, "method": method, "params": params or {}})
        response = conn.read_line(timeout=timeout)
    if response is None:
        raise RuntimeError(f"no response for {method}")
    if response.get("id") != req_id:
        raise RuntimeError(f"id mismatch for {method}: {response}")
    return response


class EventSubscription:
    """Long-lived events.subscribe connection that dispatches pushed events to a callback."""

    def __init__(self, socket_path: str | Path, subscriptions: Iterable[dict], on_event: Callable[[dict], None]):
        self.conn = HerdrPipeConnection(socket_path)
        self.req_id = f"research:events.subscribe:{uuid.uuid4().hex[:8]}"
        self.on_event = on_event
        self.events: list[dict] = []
        self.ack: dict | None = None
        self._stop = threading.Event()
        self.conn.send({"id": self.req_id, "method": "events.subscribe", "params": {"subscriptions": list(subscriptions)}})
        self.ack = self.conn.read_line(timeout=15.0)
        if not self.ack or "error" in self.ack:
            raise RuntimeError(f"subscription rejected: {self.ack}")
        self.thread = threading.Thread(target=self._pump, name="herdr-events", daemon=True)
        self.thread.start()

    def _pump(self) -> None:
        while not self._stop.is_set():
            line = self.conn.read_line()
            if line is None:
                break
            self.events.append(line)
            try:
                self.on_event(line)
            except Exception:  # research tooling: never kill the pump on a callback error
                pass

    def wait_for(self, predicate: Callable[[dict], bool], timeout: float) -> dict | None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            for event in list(self.events):
                if predicate(event):
                    return event
            time.sleep(0.05)
        return None

    def close(self) -> None:
        """Stop the pump without blocking: a synchronous ReadFile on a named pipe makes CloseHandle wait on
        Windows, so cancel the reader thread's pending I/O first (CancelSynchronousIo), then close."""
        self._stop.set()
        cancel_thread_io(self.thread)
        self.thread.join(timeout=2.0)
        if not self.thread.is_alive():
            self.conn.close()
        else:  # leave the handle to process exit rather than block the caller
            self.conn._handle = None  # type: ignore[attr-defined]


def cancel_thread_io(thread: threading.Thread) -> bool:
    """Best-effort cancellation of a thread's blocking synchronous I/O (Windows only)."""
    if os.name != "nt" or not thread.is_alive() or thread.native_id is None:
        return False
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        THREAD_TERMINATE = 0x0001
        handle = kernel32.OpenThread(THREAD_TERMINATE, False, int(thread.native_id))
        if not handle:
            return False
        try:
            return bool(kernel32.CancelSynchronousIo(handle))
        finally:
            kernel32.CloseHandle(handle)
    except Exception:
        return False


if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("HERDR_SOCKET_PATH", "")
    if not path:
        raise SystemExit("usage: herdr_socket.py <socket path>")
    print(json.dumps(request(path, "ping"), indent=2))
