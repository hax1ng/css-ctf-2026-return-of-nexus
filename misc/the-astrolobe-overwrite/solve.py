#!/usr/bin/env python3
"""Build the beacon-synchronized Ouroboros VM program and test it locally/remotely."""
import re
import socket
import sys

P = 65521
PRE = (1, 218, 59611, 783)
OPCODES = (0x10, 0x20, 0x30, 0x35, 0x40, 0x50, 0x7f, 0xff)


def transform(a):
    b = (a ^ 0x5aa5) % P
    q = pow(b, 17, P)
    q = ((q << 7) | (q >> 9)) & 0xffff
    return (q ^ 0x1337) % P


def payload(beacon):
    target = [(a + beacon) % P for a in PRE]
    regs = [0, 0, 0, 0]
    key = 0x5a
    table = list(OPCODES)
    code = bytearray()

    def emit(opcode, dst=0, hi=0, lo=0):
        nonlocal key
        code.extend(((key & 7) ^ table.index(opcode), dst, hi, lo))
        old_r0 = regs[0]
        key = (key * 31 + (old_r0 & 0xff)) & 0xff
        if opcode == 0x10:
            regs[dst] = ((hi << 8) | lo) % P
        elif opcode == 0x20:
            regs[dst] = regs[hi & 3]
        if opcode != 0x7f:
            a, b = regs[0] & 7, regs[1] & 7
            table[a], table[b] = table[b], table[a]

    for dst in (1, 2, 3, 0):
        value = target[dst]
        emit(0x10, dst, value >> 8, value & 0xff)
    for _ in range(98):
        emit(0x20, 1, 1, 0)  # MOV R1,R1, one cycle
    emit(0x7f)  # four loads + 98 moves + ten cycles = 112
    assert regs == target
    assert len(code) == 412
    return code.hex().encode() + b"\n"


def run(host, port):
    with socket.create_connection((host, port), timeout=5) as s:
        s.settimeout(5)
        received = b""
        while b"Transmitting raw telemetry vector" not in received:
            chunk = s.recv(4096)
            if not chunk:
                raise RuntimeError("service disconnected before telemetry prompt")
            received += chunk
        beacon = int(re.search(rb"BEACON: 0x([0-9A-Fa-f]+)", received).group(1), 16)
        print(f"beacon=0x{beacon:04x} registers={[(a+beacon)%P for a in PRE]}")
        s.sendall(payload(beacon))
        while True:
            try:
                chunk = s.recv(4096)
            except socket.timeout:
                break
            if not chunk:
                break
            received += chunk
    print(received.decode(errors="replace"))


if __name__ == "__main__":
    assert [transform(a) for a in PRE] == [37101, 35947, 43627, 40060]
    if len(sys.argv) == 1 or sys.argv[1] == "local":
        run("127.0.0.1", 17654)
    elif sys.argv[1] == "remote":
        run("REMOTE_HOST", 7654)
    else:
        raise SystemExit("usage: solve.py [local|remote]")
