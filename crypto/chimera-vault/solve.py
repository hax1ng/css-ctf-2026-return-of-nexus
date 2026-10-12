#!/usr/bin/env python3
"""Solve the Chimera Vault carrier, matrix and knapsack phases."""
import argparse
import ast
import base64
import re
import socket

import numpy as np


def recv_until(sock, marker):
    data = bytearray()
    while marker not in data:
        chunk = sock.recv(32768)
        if not chunk:
            raise EOFError(f"Socket closed before {marker!r}: {data[-300:]!r}")
        data.extend(chunk)
    return bytes(data)


def decode_token(telemetry):
    match = re.search(rb"telemetry stream \(Base64\):\r?\n([A-Za-z0-9+/=]+)", telemetry)
    if not match:
        raise ValueError("Cannot locate carrier")
    pcm = np.frombuffer(base64.b64decode(match.group(1)), dtype="<i2").astype(float)
    spectrum = abs(np.fft.rfft(pcm))
    # Frequencies are exact FFT bins: 0.8 s of audio gives 1.25 Hz/bin.
    freq_bins = {f: round(f * len(pcm) / 8000) for f in range(440, 2476, 5)}
    peaks = sorted(freq_bins, key=lambda f: spectrum[freq_bins[f]], reverse=True)
    top = spectrum[freq_bins[peaks[0]]]
    observed = set(f for f in peaks[:2] if spectrum[freq_bins[f]] > top / 10)
    candidates = [hi * 256 + lo for hi in range(256) for lo in range(256)
                  if 0x1000 <= hi * 256 + lo <= 0xEFFF
                  and {440 + 5*lo, 1200 + 5*hi} == observed]
    return candidates, observed


def solve_knapsack(telemetry):
    n = int(re.search(rb"System Modulus N = (\d+)", telemetry).group(1))
    modulus = int(re.search(rb"Knapsack Modulus M_mod = (\d+)", telemetry).group(1))
    matrices = {int(i): ast.literal_eval(m.decode()) for i, m in
                re.findall(rb"M_(\d) = (\[\[.*?\]\])", telemetry)}
    assert all(i in matrices for i in range(4))
    traces = [sum(matrices[i][j][j] for j in range(3)) % n for i in range(4)]
    w = (traces[1] - traces[0]) % n
    assert all((traces[i+1] - traces[i]) % n == w for i in range(3))
    weights = ast.literal_eval(re.search(rb"Knapsack Public Weights S = (\[.*?\])", telemetry).group(1).decode())
    target = int(re.search(rb"Target Resonance Sum\s*= (\d+)", telemetry).group(1))
    inverse = pow(w, -1, modulus)
    private = [weight * inverse % modulus for weight in weights]
    assert len(private) == 48
    assert all(private[i] > sum(private[:i]) for i in range(48))
    assert sum(private) < modulus
    residue = target * inverse % modulus
    bits = [0] * 48
    for i in reversed(range(48)):
        if residue >= private[i]:
            bits[i] = 1
            residue -= private[i]
    assert residue == 0
    assert sum(bit * weight for bit, weight in zip(bits, weights)) == target
    return ''.join(map(str, bits)), w


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("host")
    parser.add_argument("port", type=int)
    parser.add_argument("--max-attempts", type=int, default=6)
    args = parser.parse_args()
    for attempt in range(1, args.max_attempts + 1):
        with socket.create_connection((args.host, args.port), timeout=8) as sock:
            sock.settimeout(8)
            header = recv_until(sock, b"Enter decoded session token")
            tokens, freqs = decode_token(header)
            print(f"Attempt {attempt}: frequencies {sorted(freqs)}, token candidates {[hex(t) for t in tokens]}", flush=True)
            if len(tokens) != 1:
                print("Skipping intrinsically ambiguous carrier", flush=True)
                continue
            sock.sendall(f"{tokens[0]:#x}\n".encode())
            payload = recv_until(sock, b"Enter 48-bit solution vector")
            vector, w = solve_knapsack(header + payload)
            print(f"Recovered W={w}, vector={vector}", flush=True)
            sock.sendall((vector + "\n").encode())
            answer = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                answer += chunk
            print(answer.decode(errors="replace"), flush=True)
            if b"Flag:" in answer:
                return
            raise RuntimeError("Submission was rejected")
    raise RuntimeError("No unambiguous carrier observed")


if __name__ == "__main__":
    main()
