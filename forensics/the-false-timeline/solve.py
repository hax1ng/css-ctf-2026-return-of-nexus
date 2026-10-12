#!/usr/bin/env python3
"""Recover the emergency key from the locally extracted filesystem evidence."""

import hashlib
import sqlite3
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT = Path(__file__).resolve().parent / "extracted"
machine_id = (ROOT / "etc/machine-id").read_text().strip()
with sqlite3.connect(ROOT / "var/lib/nexus/metadata.db") as db:
    rows = db.execute(
        "SELECT session_uuid, created_at FROM jobs "
        "WHERE action='emergency_export' AND resource='emergency-core' "
        "AND status='completed'"
    ).fetchall()
assert len(rows) == 1, rows
session_uuid, event_epoch = rows[0]
key_material = f"{machine_id}|{session_uuid}|{int(event_epoch)}"
key = hashlib.sha256(key_material.encode()).digest()
data = (ROOT / "var/cache/nexus/.ekey-cache").read_bytes()
assert data.startswith(b"NXKEY_V1")
print(AESGCM(key).decrypt(data[8:20], data[20:], None).decode())
