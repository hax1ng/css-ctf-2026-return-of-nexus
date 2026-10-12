#!/usr/bin/env python3
"""FLAPPY BOARD automated client.

Reproduces the exact HTTP protocol of the `flappy_board` ELF client, but skips
the GUI and the purely client-side "corrupted departure timer" wait, driving
the three scored rounds via replays generated offline by flappy_engine.py.

Protocol (base URL default http://REMOTE_HOST:8765), all requests send
  Content-Type: application/x-www-form-urlencoded
and, once obtained, Authorization: Bearer <token>:

  POST /api/attempt   (empty body)  -> token=<64>&round=1&target=10
  GET  /api/attempt                 -> round&seed&target&wait_seconds&remaining_seconds
  POST /api/complete  round=&wait_ms=<ws*1000>&ticks=&score=&flaps=i0,i1,...
                                    -> next round params, or round=4&flag=CSSCTF{...}

Practice oracle (safe server-side physics check, single chunk while ticks<6000):
  POST /api/practice  (empty body)  -> seed=&token=<64>
  POST /api/practice/check  (Bearer practice-token)
        sequence=0&ticks=&final=1&score=&flaps=... -> verified_score=&complete=1

NETWORK IS OFF BY DEFAULT.  --selftest runs solver only (no network).
The network subcommands require --go, and the endpoint must be authorized
out-of-band (ctfdctl confirm-endpoint 27 http://REMOTE_HOST:8765).
"""
from __future__ import annotations
import argparse
import sys
import time
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime

import flappy_engine as fe

DEFAULT_SERVER = "http://REMOTE_HOST:8765"
UA = "flappy-board-solver"
TARGETS = {1: 10, 2: 20, 3: 30}


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open("solve_log.txt", "a") as f:
            f.write(line + "\n")
    except OSError:
        pass


class Client:
    def __init__(self, base: str, timeout: float = 10.0):
        self.base = base.rstrip("/")
        self.timeout = timeout
        self.token = None            # main attempt bearer token

    def _request(self, path: str, body, bearer):
        """body=None -> GET ; body=str -> POST (empty string allowed)."""
        url = self.base + path
        headers = {"Content-Type": "application/x-www-form-urlencoded",
                   "User-Agent": UA}
        if bearer:
            headers["Authorization"] = "Bearer " + bearer
        data = None
        method = "GET"
        if body is not None:
            data = body.encode()
            method = "POST"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return r.getcode(), r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace")

    @staticmethod
    def parse(body: str) -> dict:
        # server replies as x-www-form-urlencoded key=value&key=value
        out = {}
        for k, v in urllib.parse.parse_qsl(body, keep_blank_values=True):
            out[k] = v
        return out

    # -- scored flow ---------------------------------------------------------
    def new_attempt(self):
        code, body = self._request("/api/attempt", "", self.token)
        log(f"POST /api/attempt -> {code} {body[:200]!r}")
        if code != 200:
            raise RuntimeError(f"/api/attempt failed HTTP {code}: {body[:200]}")
        d = self.parse(body)
        tok = d.get("token", "")
        if len(tok) != 64:
            raise RuntimeError(f"bad token len {len(tok)}: {body[:200]}")
        self.token = tok
        log(f"token acquired (round={d.get('round')} target={d.get('target')})")
        return d

    def get_round(self):
        code, body = self._request("/api/attempt", None, self.token)
        log(f"GET  /api/attempt -> {code} {body[:200]!r}")
        if code != 200:
            raise RuntimeError(f"GET /api/attempt failed HTTP {code}: {body[:200]}")
        return self.parse(body)

    def complete(self, rnd, wait_ms, ticks, score, flaps):
        flapstr = ",".join(map(str, flaps))
        body = f"round={rnd}&wait_ms={wait_ms}&ticks={ticks}&score={score}&flaps={flapstr}"
        code, resp = self._request("/api/complete", body, self.token)
        log(f"POST /api/complete round={rnd} ticks={ticks} score={score} "
            f"flaps={len(flaps)} wait_ms={wait_ms} -> {code} {resp[:240]!r}")
        if code != 200:
            raise RuntimeError(f"/api/complete failed HTTP {code}: {resp[:240]}")
        return self.parse(resp)

    # -- practice oracle -----------------------------------------------------
    def practice(self):
        code, body = self._request("/api/practice", "", self.token)
        log(f"POST /api/practice -> {code} {body[:200]!r}")
        if code != 200:
            raise RuntimeError(f"/api/practice failed HTTP {code}: {body[:200]}")
        d = self.parse(body)
        ptok = d.get("token", "")
        seed = int(d["seed"])
        if len(ptok) != 64:
            raise RuntimeError(f"bad practice token len {len(ptok)}")
        return seed, ptok

    def practice_check(self, ptok, ticks, score, flaps, final=1, sequence=0):
        flapstr = ",".join(map(str, flaps))
        body = (f"sequence={sequence}&ticks={ticks}&final={final}"
                f"&score={score}&flaps={flapstr}")
        code, resp = self._request("/api/practice/check", body, ptok)
        log(f"POST /api/practice/check -> {code} {resp[:240]!r}")
        if code != 200:
            raise RuntimeError(f"/api/practice/check failed HTTP {code}: {resp[:240]}")
        return self.parse(resp)


def do_practice(cli: Client, practice_target: int = 30):
    """Server-side physics sanity check; consumes no scored round."""
    cli.new_attempt()
    seed, ptok = cli.practice()
    log(f"practice seed={seed} target={practice_target}")
    ticks, score, flaps = fe.solve_seed(seed, practice_target, verbose=True)
    ok, s, t, dead = fe.verify_replay(seed, practice_target, flaps, ticks)
    log(f"local replay: ticks={ticks} score={score} flaps={len(flaps)} verify_ok={ok}")
    if not ok:
        raise RuntimeError("local replay failed self-verification; aborting")
    if ticks >= 6000:
        log("WARNING: practice run exceeds one 6000-tick chunk; not handled here")
    res = cli.practice_check(ptok, ticks, score, flaps, final=1, sequence=0)
    vs = res.get("verified_score")
    log(f"SERVER verified_score={vs} complete={res.get('complete')} "
        f"cheated={res.get('cheated')} (expected {score})")
    if res.get("cheated") == "1":
        raise RuntimeError("server flagged replay as cheated")
    if vs is not None and int(vs) == score and res.get("complete") == "1":
        log("PRACTICE OK: server physics matches our simulator exactly.")
        return True
    log("PRACTICE MISMATCH: investigate before running scored rounds.")
    return False


def do_solve(cli: Client):
    d = cli.new_attempt()
    # fetch round-1 parameters
    d = cli.get_round()
    flag = None
    while True:
        rnd = int(d["round"])
        if rnd == 4 or "flag" in d:
            flag = d.get("flag")
            log(f"ROUND 4 reached. flag field: {flag!r}")
            break
        seed = int(d["seed"])
        target = int(d.get("target", TARGETS.get(rnd, 0)))
        wait_seconds = int(d.get("wait_seconds", 0))
        rem = d.get("remaining_seconds")
        log(f"--- ROUND {rnd}: seed={seed} target={target} "
            f"wait_seconds={wait_seconds} remaining_seconds={rem} ---")
        if target != TARGETS.get(rnd):
            log(f"WARNING: unexpected target {target} for round {rnd}")
        t0 = time.time()
        ticks, score, flaps = fe.solve_seed(seed, target, verbose=True)
        ok, s, tk, dead = fe.verify_replay(seed, target, flaps, ticks)
        log(f"solved in {time.time()-t0:.2f}s: ticks={ticks} score={score} "
            f"flaps={len(flaps)} verify_ok={ok} (dead={dead})")
        if not ok:
            raise RuntimeError(f"round {rnd} replay failed self-verify; aborting")
        wait_ms = wait_seconds * 1000
        d = cli.complete(rnd, wait_ms, ticks, score, flaps)
    if flag:
        log("=" * 60)
        log(f"FLAG: {flag}")
        log("=" * 60)
        with open("flag.txt", "w") as f:
            f.write(flag + "\n")
    else:
        log("No flag field in round-4 response; full response was logged above.")
    return flag


def selftest():
    import random
    rng = random.Random(42)
    fails = 0
    for _ in range(60):
        seed = rng.randrange(1, 1 << 32)
        for tgt in (10, 20, 30):
            ticks, score, flaps = fe.solve_seed(seed, tgt)
            ok, s, t, dead = fe.verify_replay(seed, tgt, flaps, ticks)
            if not ok:
                fails += 1
                print(f"FAIL seed={seed} target={tgt} score={s} dead={dead}")
    print(f"selftest done: {fails} failures / 180 solves")
    return fails == 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["selftest", "practice", "solve"],
                    help="selftest=offline only; practice/solve need --go")
    ap.add_argument("--server", default=DEFAULT_SERVER)
    ap.add_argument("--timeout", type=float, default=10.0)
    ap.add_argument("--go", action="store_true",
                    help="required to actually touch the network")
    a = ap.parse_args()

    if a.mode == "selftest":
        sys.exit(0 if selftest() else 1)

    if not a.go:
        print("Refusing network access without --go. The endpoint must be "
              "authorized first (ctfdctl confirm-endpoint 27 <endpoint>).")
        sys.exit(2)

    cli = Client(a.server, timeout=a.timeout)
    log(f"=== {a.mode} against {a.server} @ {datetime.now().isoformat()} ===")
    if a.mode == "practice":
        do_practice(cli)
    else:
        do_solve(cli)


if __name__ == "__main__":
    main()
