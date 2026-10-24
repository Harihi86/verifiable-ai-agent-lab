"""Focused check: does events.subscribe deliver workspace.created to an external raw client?"""
from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import herdr_isolated as hi  # noqa: E402
import herdr_socket as hs  # noqa: E402


def main() -> int:
    rt = hi.IsolatedRuntime(session_name=hi.unique_session_name("wsev"))
    rt.prepare()
    rt.write_resolution_record()
    proc = rt.start_server()
    out: dict = {"session": rt.session_name}
    try:
        assert rt.wait_for_ping(timeout=40)
        _, sessions = rt.run_json("session", "list", "--json")
        sock = next(s["socket_path"] for s in sessions["sessions"] if s["name"] == rt.session_name)
        conn = hs.HerdrPipeConnection(sock)
        conn.send({"id": "sub1", "method": "events.subscribe", "params": {"subscriptions": [
            {"type": "workspace.created"}, {"type": "workspace.focused"}, {"type": "tab.created"}, {"type": "layout.updated"}]}})
        out["ack"] = conn.read_line(timeout=10)
        received: list = []

        def pump():
            while True:
                try:
                    line = conn.read_line()
                except Exception as err:  # noqa: BLE001
                    received.append({"pump_error": repr(err)})
                    return
                if line is None:
                    received.append({"pump_eof": True})
                    return
                received.append(line)

        t = threading.Thread(target=pump, daemon=True)
        t.start()
        time.sleep(0.5)
        wd = rt.tmp_dir / "p1"
        wd.mkdir(exist_ok=True)
        c, payload = rt.run_json("workspace", "create", "--cwd", str(wd), "--label", "one", "--no-focus")
        out["create_exit"] = c.returncode
        time.sleep(3.0)
        c2, payload2 = rt.run_json("workspace", "create", "--cwd", str(wd), "--label", "two")
        time.sleep(3.0)
        out["received"] = received[:10]
        out["received_count"] = len(received)
        # Compare with the documented one-shot events.wait helper, if available
        try:
            w = hs.request(sock, "events.wait", {"subscriptions": [{"type": "workspace.created"}], "timeout_ms": 1000})
            out["events_wait_probe"] = w
        except Exception as err:  # noqa: BLE001
            out["events_wait_probe"] = repr(err)
        conn.close()
    finally:
        out["server_exit"] = rt.stop_server(proc)
        (rt.log_dir / "debug-ws-events.json").write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(json.dumps(out, indent=2, default=str)[:4000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
