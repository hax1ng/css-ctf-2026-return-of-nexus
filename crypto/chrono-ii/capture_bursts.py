#!/usr/bin/env python3
"""Concurrent Chrono II capture; run only after human endpoint confirmation.

Usage (after confirmation):
    python3 capture_bursts.py --confirmed-endpoint http://REMOTE_HOST:8001

Records five simultaneous requests near the middle of one second and another
five just after the next second boundary. Complete bodies are saved as base64;
compare the extracted ciphertext field, not merely the whole-body digest.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import time

from capture_timed import ENDPOINT, capture


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirmed-endpoint", required=True)
    args = parser.parse_args()
    if args.confirmed_endpoint != ENDPOINT:
        parser.error("The endpoint must exactly match the human-confirmed team instance")
    first_sec = time.time_ns() // 1_000_000_000 + 2
    output = Path(__file__).with_name(f"burst_samples_{first_sec}.jsonl")
    with ThreadPoolExecutor(max_workers=10) as pool, output.open("x", encoding="utf-8") as stream:
        futures = []
        for burst, offset_ns in ((0, 500_000_000), (1, 50_000_000)):
            target_ns = (first_sec + burst) * 1_000_000_000 + offset_ns
            futures.extend((burst, pool.submit(capture, target_ns, burst * 5 + i)) for i in range(5))
        for burst, future in futures:
                record = future.result()
                record["burst"] = burst
                stream.write(json.dumps(record) + "\n")
                stream.flush()
                print(burst, record["index"], record["started_utc"],
                      record["date_header"], record["status"], record["body_len"],
                      record["error"])
    print(f"Saved complete responses to {output}")


if __name__ == "__main__":
    main()
