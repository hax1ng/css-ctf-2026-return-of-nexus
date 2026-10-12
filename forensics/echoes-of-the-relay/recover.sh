#!/usr/bin/env bash
# Echoes of the Relay — recover the operator's final transmission.
# Requires relay_backup.img (32 MiB ext4 image, omitted from this repo for size)
# and the Sleuth Kit (fls / istat / icat) + unzip.
set -euo pipefail
IMG=${1:-relay_backup.img}

# 1. List deleted entries; the note is at inode 25 (unallocated, zero links).
fls -r -p "$IMG" | grep -i emergency_note
istat "$IMG" 25

# 2. Recover the deleted operator note -> archive password severance2101.
icat "$IMG" 25 | tee recovered/emergency_note.txt

# 3. The live picture (inode 24) is a PNG with a ZIP appended after IEND.
icat "$IMG" 24 > relay_status.png
unzip -l relay_status.png                      # lists transmission/*
unzip -P severance2101 relay_status.png        # extracts the transmission

# 4. The flag is in the recovered transmission.
grep -aoE 'CSSCTF\{[^}]*\}' transmission/core_recovery.txt
