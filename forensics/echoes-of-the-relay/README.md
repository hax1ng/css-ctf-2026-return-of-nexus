# Echoes of the Relay

**Category:** Forensics · **Points:** 33 · **Solves:** 361 · **Challenge ID:** 1

> The terminal's final operator tried to preserve something before the system shut down. Recover the operator's final transmission.

## Challenge

The Kuiper Belt Relay was one of the first Nexus nodes to come back online after
the Severance — for exactly 47 seconds. Before it went silent again, an automated
recovery system transmitted a damaged storage image from one of its maintenance
terminals. Nexus engineers inspected the *visible* files and found nothing useful,
but the terminal's final operator apparently hid something before shutdown.

**Attachment:** `relay_backup.img` (32 MiB raw disk image — omitted here for size, see [Files](#files)).

## Initial analysis

The image is a raw ext4 filesystem:

```console
$ file relay_backup.img
relay_backup.img: Linux rev 1.0 ext4 filesystem data ...
```

Mounting and browsing the *live* tree shows only innocuous files
(`operator/Pictures/relay_status.png`, etc.) — exactly what the engineers saw. The
hint ("tried to preserve something") points at two classic forensic layers that a
casual browse misses: **deleted inodes** and **data appended after a file's logical
end**.

Walking the inode table with the Sleuth Kit surfaces a deleted entry:

```console
$ fls -r -p relay_backup.img | grep emergency_note
-/r * 25:   operator/Documents/emergency_note.txt
$ istat relay_backup.img 25        # unallocated, 0 links — a deleted file
```

## Vulnerability / core concept

Two-stage recovery:

1. **Deleted-file recovery.** Unlinking a file on ext4 clears the directory entry
   but the inode's data blocks survive until reused. `icat` reads the blocks
   directly by inode number, recovering the operator's note — which hands over the
   method and a password.
2. **Trailing-data carving (PNG + appended ZIP).** The "normal" picture is a valid
   PNG whose `IEND` chunk is *not* the end of the file: a ZIP archive is concatenated
   after it. Image viewers stop at `IEND` and show a harmless status image, so the
   payload is invisible to a visual inspection ("Look beyond what the image viewer
   shows you").

## Exploitation

Recover the deleted note first:

```console
$ icat relay_backup.img 25
NX-17 PERSONAL NOTE
They are wiping the relay.
I couldn't leave the transmission as a normal file.
I attached the recovery package to the diagnostic image before the node went offline.
    archive password = severance2101
Look beyond what the image viewer shows you.
-NX17
```

So the picture (`relay_status.png`, inode 24) carries an appended, password-protected
archive. Carve the file out and confirm the structure — the PNG `IEND` ends at byte
19274, immediately followed by a ZIP local-file header (`PK\x03\x04`):

```console
$ icat relay_backup.img 24 > relay_status.png
$ unzip -l relay_status.png
warning: 19274 extra bytes at beginning or within zipfile
  Length      Name
      155     transmission/manifest.txt
       83     transmission/core_recovery.txt
```

Extract with the recovered password:

```console
$ unzip -P severance2101 relay_status.png
$ cat transmission/core_recovery.txt
The Nexus remembers what the filesystem forgets.
CSSCTF{d3l3t3d_d03snt_m34n_g0n3}
```

`transmission/manifest.txt` corroborates the source (`KUIPER-RELAY-04`) and operator
(`NX-17`). The whole flow is scripted in [`recover.sh`](recover.sh); the recovered
artifacts are committed under [`recovered/`](recovered/).

## Flag

```
CSSCTF{d3l3t3d_d03snt_m34n_g0n3}
```

## Files

- `relay_backup.img` — 32 MiB ext4 image, **omitted** (reproducible challenge input).
  SHA-256 `8e781d3620ef79ec9ae2068a36d89cac615918e612559d29580452fecafb38a2`.
- `recovered/emergency_note.txt` — the deleted operator note (inode 25).
- `recovered/transmission/{core_recovery.txt,manifest.txt}` — extracted from the ZIP
  appended to inode 24's PNG.

## Key takeaways

- A deleted file is only unlinked, not erased — `fls`/`istat`/`icat` read the inode's
  blocks directly.
- `IEND` is where an image viewer stops, not where the file ends; always check for
  trailing bytes after a valid image.
- Follow the breadcrumbs in order: the deleted note is what tells you the picture is a
  carrier and gives you the archive password.
