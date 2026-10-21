#!/usr/bin/env python3
"""Local server for the CMs <-> Unicode elicitation editor.

Serves the static page and, on every change the page makes, writes the whole
editor state to ``state/state.json`` plus a readable digest to
``state/latest.md``.  That is how the mapping work becomes visible without the
person using the page having to copy, export or save anything.

    python3 server.py --open
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import threading
import time
import webbrowser
from collections import Counter
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
STATE_DIR = HERE / "state"
STATE_FILE = STATE_DIR / "state.json"
EVENTS_FILE = STATE_DIR / "events.jsonl"
LATEST_FILE = STATE_DIR / "latest.md"

INVISIBLE = {0x180B, 0x180C, 0x180D, 0x180E, 0x180F, 0x202F, 0x200C, 0x200D, 0xFEFF}

VERDICTS = ("same", "variant", "component", "missing", "skip")


def show(text: str) -> str:
    """Make invisible format characters visible, so they cannot be lost in a read."""
    return "".join(
        f"‹U+{ord(character):04X}›" if ord(character) in INVISIBLE else character
        for character in str(text)
    )


def dump_json(value: Any, *, indent: int | None = 2) -> str:
    """JSON with invisible characters kept as escapes, never as literals."""
    text = json.dumps(value, ensure_ascii=False, indent=indent)
    for code_point in INVISIBLE:
        text = text.replace(chr(code_point), f"\\u{code_point:04x}")
    return text


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def write_state(data: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    temporary = STATE_FILE.with_suffix(".json.tmp")
    temporary.write_text(dump_json(data) + "\n")
    os.replace(temporary, STATE_FILE)

    with EVENTS_FILE.open("a") as events:
        events.write(
            json.dumps(
                {
                    "ts": now(),
                    "revision": data.get("revision"),
                    "current": data.get("current"),
                    "action": data.get("lastAction"),
                    "stats": data.get("stats"),
                },
                ensure_ascii=False,
            )
            + "\n"
        )

    try:
        LATEST_FILE.write_text(digest(data))
    except Exception as error:  # the digest must never block saving the state
        LATEST_FILE.write_text(
            "# CMs ↔ Unicode — editor state\n\n"
            f"- updated: {show(data.get('updated') or now())}\n"
            f"- revision: {data.get('revision', 0)}\n"
            f"- progress: {(data.get('stats') or {}).get('doneDefaults', '?')}"
            f"/{(data.get('stats') or {}).get('defaults', '?')} default\n\n"
            f"_digest error: {type(error).__name__}: {error}_\n"
        )


def digest(data: dict) -> str:
    items = data.get("items") or {}
    verdicts = Counter(
        record.get("verdict") for record in items.values() if record.get("verdict")
    )
    stats = data.get("stats") or {}
    current = data.get("current")
    current_record = items.get(current) or {}

    lines = [
        "# CMs ↔ Unicode — editor state",
        "",
        f"- updated: {show(data.get('updated') or now())}",
        f"- revision: {data.get('revision', 0)}",
        f"- family: {show(data.get('family', ''))}",
        f"- current: `{show(current or '—')}` — {show(data.get('currentLabel') or current_record.get('label') or '—')}",
        f"- typed: `{show(current_record.get('typed', '')) or '—'}`",
        f"- note: {show(current_record.get('note', '')) or '—'}",
        f"- progress: {stats.get('doneDefaults', '?')}/{stats.get('defaults', '?')} default, "
        f"{stats.get('doneAll', '?')}/{stats.get('all', '?')} all",
        "",
        "## Verdicts",
        "",
    ]
    for verdict in VERDICTS:
        lines.append(f"- {verdict}: {verdicts.get(verdict, 0)}")
    lines.append(f"- unconfirmed records: {len(items) - sum(verdicts.values())}")

    recent = [
        (record, item_id)
        for item_id, record in items.items()
        if record.get("verdict") and record.get("ts")
    ]
    recent.sort(key=lambda pair: (pair[0].get("ts", 0), pair[1]), reverse=True)

    lines += ["", "## Last 15 verdicts", ""]
    if not recent:
        lines.append("_none yet_")
    for record, item_id in recent[:15]:
        try:
            stamp = datetime.fromtimestamp(float(record["ts"]) / 1000).strftime("%H:%M:%S")
        except (TypeError, ValueError, OSError):
            stamp = "—"
        note = f" — {show(record['note'])}" if record.get("note") else ""
        lines.append(
            f"- `{stamp}` **{record['verdict']}** {show(record.get('label') or item_id)} "
            f"← keys `{show(record.get('typed', ''))}`{note}"
        )

    free = data.get("free") or {}
    lines += [
        "",
        "## Free mode",
        "",
        f"- unicode: {show(free.get('unicode', '')) or '—'}",
        f"- legacy: `{show(free.get('legacy', '')) or '—'}`",
    ]

    pairs = data.get("freePairs") or []
    lines += ["", f"## Saved pairs ({len(pairs)})", ""]
    if not pairs:
        lines.append("_none yet_")
    for number, pair in enumerate(reversed(pairs[-10:]), start=1):
        lines.append(
            f"{number}. {show(pair.get('unicode', ''))} ← `{show(pair.get('legacy', ''))}` "
            f"({show(pair.get('family', ''))})"
        )

    lines.append("")
    return "\n".join(lines)


class Handler(SimpleHTTPRequestHandler):
    server_version = "CMsEditor/1.0"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(HERE), **kwargs)

    def end_headers(self) -> None:
        if self.path.startswith("/api/") or self.path.endswith(
            (".html", ".js", ".css", ".json")
        ):
            self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self) -> None:
        if self.path.startswith("/api/state"):
            payload = STATE_FILE.read_bytes() if STATE_FILE.exists() else b"{}"
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        super().do_GET()

    def do_POST(self) -> None:
        if not self.path.startswith("/api/state"):
            self.send_error(404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_error(400)
            return

        if length <= 0 or length > 5_000_000:
            self.send_error(413)
            return

        body = self.rfile.read(length)
        try:
            data = json.loads(body)
            if not isinstance(data, dict):
                raise ValueError("state must be an object")
        except (ValueError, json.JSONDecodeError) as error:
            self.send_error(400, str(error))
            return

        write_state(data)
        record = (data.get("items") or {}).get(data.get("current") or "") or {}
        print(
            f"{datetime.now().strftime('%H:%M:%S')}  "
            f"{data.get('family', '?')}  "
            f"{data.get('current', '?')}  "
            f"{record.get('verdict', '…')}  "
            f"keys={record.get('typed', '')!r}  "
            f"({(data.get('stats') or {}).get('doneDefaults', '?')}"
            f"/{(data.get('stats') or {}).get('defaults', '?')})",
            flush=True,
        )

        self.send_response(204)
        self.end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        if self.path.startswith("/api/"):
            return
        sys.stderr.write("%s  %s\n" % (self.log_date_time_string(), format % args))


def find_port(preferred: int) -> int:
    for port in range(preferred, preferred + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise SystemExit(f"no free port between {preferred} and {preferred + 19}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--open", action="store_true", help="open the page in the browser")
    args = parser.parse_args()

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    port = find_port(args.port)
    url = f"http://127.0.0.1:{port}/"
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)

    print(f"CMs ↔ Unicode editor on {url}")
    print(f"state: {STATE_FILE}")
    print("Ctrl-C to stop.")

    if args.open:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
