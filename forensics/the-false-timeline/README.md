# The False Timeline

**Category:** Forensics · **Points:** 66 · **Solves:** 431 · **Challenge ID:** 2

> Investigators concluded KAI-7 performed the export at 03:17. There is one problem: KAI-7 had already disconnected. Someone wanted the investigation to end there.

## Challenge

Nexus Incident Response recovered a filesystem image from Relay **NX-17** after an
unauthorised emergency key export. The application log blames Relay Administrator
**KAI-7**, timestamping the export at ~03:17 — but KAI-7's session had already closed.
Reconstruct the *true* incident timeline and recover the stolen emergency access key.

**Attachment:** `nexus_relay.img.xz` (compresses a 128 MiB ext4 image — omitted here,
see [Files](#files)).

## Initial analysis

Decompress and carve the relevant inodes read-only with the Sleuth Kit (`icat`). The
interesting artifacts, committed under [`extracted/`](extracted/):

| Path | Role |
|------|------|
| `var/log/nexus/relay.log` | Application log — the *false* story |
| `var/log/auth.log` | SSH / su session truth |
| `var/log/audit/audit.log` | Kernel auditd — syscall-level truth |
| `var/lib/nexus/metadata.db` | SQLite: `sessions` + `jobs` |
| `opt/nexus/lib/exporter.py` | How the export key is derived |
| `var/cache/nexus/.ekey-cache` | The encrypted emergency key |
| `etc/machine-id` | Host identifier used in key derivation |

There is no compiled executable — `nx-export` is a one-line shell stub; the real logic
is in `exporter.py`.

## Vulnerability / core concept

**Timeline tampering.** The attacker leaned on the fact that an analyst will trust the
first, most human-readable log. `relay.log` says:

```
2101-10-01T03:17:03+10:00 relay-core: WARN export request accepted principal=KAI-7 resource=emergency-core
```

But three independent sources contradict it. `auth.log` shows KAI-7 logged out and then
a `su` to the service account:

```
02:52:11  Accepted publickey for kai ... session opened for user kai
03:05:41  session closed for user kai            <-- KAI-7 gone
03:10:02  Successful su for svc-relay by root    <-- someone else takes over
```

`metadata.db` attributes the actual job to `svc-relay`, not KAI-7:

```
sessions: b7a1c8d9-... KAI-7     ends epoch 4157543141 (03:05:41)
sessions: aab0c8b2-... svc-relay starts 4157543482, (never closed)
jobs:     2  session=aab0c8b2-...  emergency_export  emergency-core  completed  4157543568
```

And `audit.log` shows the real chain of events under `svc-relay` (uid 998), including the
**anti-forensic touch** that planted the misleading mtime:

```
:88  sh            (svc-relay)                 epoch 4157543482  03:11:22
:92  nx-export --emergency (svc-relay)         epoch 4157543568  03:12:48   <-- real export
:99  touch -r /etc/machine-id .../.ekey-cache  epoch 4157543712  03:15:12   <-- backdated the cache
```

(The event 99 `proctitle` hex decodes to
`touch -r /etc/machine-id /var/cache/nexus/.ekey-cache`.) So the cache's mtime was
copied from `machine-id` to hide the true write time; the real export happened at
**03:12:48**, under session `aab0c8b2-...` / `svc-relay` — *not* the 03:17 KAI-7 event the
app log invented.

## Exploitation

`exporter.py` derives the AES-256-GCM key deterministically from the execution context:

```python
material = f"{machine_id.strip()}|{session_uuid.strip()}|{int(event_epoch)}"
key = hashlib.sha256(material.encode()).digest()
# on-disk blob: b"NXKEY_V1" + 12-byte nonce + ciphertext||tag
```

All three inputs are recoverable from the evidence — and must be the *true* ones, not the
decoy 03:17/KAI-7 values:

- `machine_id` = `etc/machine-id`
- `session_uuid` / `event_epoch` = the `emergency_export` row in `metadata.db`
  (session `aab0c8b2-f8b1-4f11-9a72-6d8123a1005a`, epoch `4157543568`)

[`solve.py`](solve.py) pulls those, derives the key, and runs AES-GCM *authenticated*
decryption over `.ekey-cache`. GCM's tag check means a wrong context fails loudly — a
successful decrypt confirms the correct timeline:

```console
$ python3 solve.py
CSSCTF{kai_did_not_do_it}
```

## Flag

```
CSSCTF{kai_did_not_do_it}
```

## Files

- `nexus_relay.img.xz` — official attachment; expands to a 128 MiB ext4 image.
  **Omitted** (reproducible challenge input). The small evidence inodes it contains are
  committed under `extracted/`.
- `extracted/` — the carved evidence subtree (`auth.log`, `audit/audit.log`, `relay.log`,
  `metadata.db`, `exporter.py`, `.ekey-cache`, `machine-id`, …) — enough for `solve.py` to
  run end-to-end.

## Key takeaways

- Never trust a single log. Cross-reference the application log against `auth.log`,
  auditd, and any database — the attacker only bothered to forge the friendly one.
- `touch -r` copies a reference file's timestamps; a cache whose mtime exactly matches
  `/etc/machine-id` is a red flag. ctime/birth time (and the audit record) betray the
  real write.
- AES-GCM makes a great correctness oracle: if your reconstructed key/context is wrong,
  the tag verification fails, so a clean decrypt *is* the proof your timeline is right.
