#!/usr/bin/env python3
"""Capture Chrono II responses ONLY after exact team-endpoint confirmation.

Usage after human confirmation:
  python3 capture_timed.py --confirmed-endpoint http://REMOTE_HOST:8001

Writes the complete bodies (base64) and timing/headers to a local JSONL file.
"""

import argparse
import base64
import datetime as dt
import hashlib
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

ENDPOINT = "http://REMOTE_HOST:8001"


def capture(target_ns, index):
    while time.time_ns() < target_ns:
        time.sleep(min((target_ns - time.time_ns()) / 1e9, 0.01))
    started_ns = time.time_ns()
    started_mono_ns = time.monotonic_ns()
    req = urllib.request.Request(ENDPOINT, headers={"Cache-Control": "no-cache"})
    error = None
    try:
        response = urllib.request.urlopen(req, timeout=5)
    except urllib.error.HTTPError as exc:
        response = exc
    except Exception as exc:
        response = None
        error = repr(exc)
    if response is not None:
        with response:
            body = response.read()
            status = response.status
            headers = list(response.headers.items())
    else:
        body, status, headers = b"", None, []
    ended_ns = time.time_ns()
    return {
        "index": index,
        "scheduled_ns": target_ns,
        "started_ns": started_ns,
        "ended_ns": ended_ns,
        "started_utc": dt.datetime.fromtimestamp(started_ns / 1e9, dt.timezone.utc).isoformat(),
        "ended_utc": dt.datetime.fromtimestamp(ended_ns / 1e9, dt.timezone.utc).isoformat(),
        "duration_monotonic_ns": time.monotonic_ns() - started_mono_ns,
        "status": status,
        "date_header": next((v for k, v in headers if k.lower() == "date"), None),
        "headers": headers,
        "body_len": len(body),
        "body_sha256": hashlib.sha256(body).hexdigest(),
        "body_b64": base64.b64encode(body).decode("ascii"),
        "error": error,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirmed-endpoint", required=True)
    args = parser.parse_args()
    if args.confirmed_endpoint != ENDPOINT:
        parser.error("The confirmed endpoint must match the exact advertised address")
    # Start next whole-second epoch, with three requests inside each of three
    # consecutive seconds. Actual timings are preserved; don't assume that a
    # delayed request landed in its scheduled second.
    first_sec = time.time_ns() // 1_000_000_000 + 2
    targets = [
        first_sec * 1_000_000_000 + second * 1_000_000_000 + offset
        for second in range(3)
        for offset in (150_000_000, 350_000_000, 550_000_000)
    ]
    output = Path(__file__).with_name(f"timed_samples_{first_sec}.jsonl")
    with output.open("x", encoding="utf-8") as stream:
        for index, target in enumerate(targets):
            record = capture(target, index)
            stream.write(json.dumps(record) + "\n")
            stream.flush()
            print(index, record["started_utc"], record["date_header"],
                  record["status"], record["body_len"], record["body_sha256"],
                  record["error"])
    print(f"Saved complete responses to {output}")


if __name__ == "__main__":
    main()
