# Dockside Ticket Office

**Category:** Pwn · **Points:** 25 · **Solves:** 348 · **Challenge ID:** 3

> A cancelled ticket should no longer be usable, but this old terminal may not handle ticket memory safely.

## Challenge

The dockside ticket office manages temporary harbour access tickets. You can
create, cancel, edit, and use a ticket. A cancelled ticket should no longer be
usable, but this old terminal may not handle ticket memory safely — can you turn
a cancelled ticket into emergency harbour access?

Flag format: `CSSCTF{}`

**Attachments**

- `dockside_ticket` — the challenge binary (~16 KB).

## Initial analysis

```
$ file dockside_ticket
dockside_ticket: ELF 64-bit LSB executable, x86-64, dynamically linked,
                 interpreter /lib64/ld-linux-x86-64.so.2, not stripped
```

Mitigations (via `readelf`): **No PIE** (`ET_EXEC`, so every address is fixed),
NX enabled, Partial RELRO, stack canary present. The binary is **not stripped**,
so the menu handlers keep their names.

It is a classic menu-driven heap program with a single global `active_ticket`
pointer to a `0x28`-byte heap chunk. The relevant handlers:

- `create_ticket()` — `malloc(0x28)`, stores it in `active_ticket`, and
  initialises a **function pointer at offset `+0x20`** of the chunk.
- `cancel_ticket()` — `free(active_ticket)` **without clearing the global** →
  the pointer dangles.
- `edit_ticket()` — `read(0, active_ticket, 0x28)` straight through that
  (now dangling) pointer → a write of `0x28` bytes = `0x20` data bytes plus the
  8-byte function pointer at `+0x20`.
- `use_ticket()` — **calls the function pointer at `active_ticket + 0x20`**.
- `open_gate()` at `0x40125f` — prints the flag. This is the win function.

## Vulnerability / core concept

Textbook **use-after-free into a function-pointer hijack**. `cancel_ticket()`
frees the chunk but leaves `active_ticket` pointing at it; `edit_ticket()` then
writes 40 bytes through the dangling pointer, letting us overwrite the freed
chunk's function pointer at `+0x20`; `use_ticket()` invokes it. Because the
binary is No-PIE, the win function's address is a fixed constant, so no leak is
needed — we just point the function pointer straight at `open_gate`.

## Exploitation

Drive the menu in order: **create → cancel → edit → use**.

```
1) create   -> malloc(0x28), fn ptr set at +0x20
2) cancel   -> free(), active_ticket now dangling
3) edit     -> read(0, active_ticket, 0x28) over the freed chunk
4) use      -> call *(active_ticket + 0x20) -> open_gate()
```

The `edit` payload overwrites the 32 bytes of data and then the function
pointer with the entry of `open_gate`:

```python
payload = b"A" * 0x20 + struct.pack("<Q", 0x40125F)  # open_gate entry
#          \__ 32 filler __/  \____ overwrites fn ptr at +0x20 ____/
```

Two gotchas that cost time (recorded in the solve notes):

- A one-shot piped payload failed because stdio `scanf` buffers ahead of the raw
  `read` in `edit`. Writing input **interactively** — one menu prompt at a time —
  fixes it. `solve_local.py` does exactly this with a `read_until(prompt)` loop.
- The win address must be the function **entry** `0x40125f`. An earlier attempt
  at `0x401271` landed in the middle of `open_gate` and failed.

`solve_local.py` runs the target through the loader
(`/lib64/ld-linux-x86-64.so.2 ./dockside_ticket`), performs create → cancel →
edit → use, and asserts the flag appears. Local output: `Ticket scanned.`,
`Emergency harbour access granted.`, and the flag.

## Flag

```
CSSCTF{us3_4ft3r_fr33_d0cks1d3}
```

## Key takeaways

- `free()` without nulling the pointer is a use-after-free waiting to happen.
- A heap object that stores a function pointer turns a write-after-free straight
  into control-flow hijack — and with No-PIE you don't even need an info leak.
- Mind buffered stdio versus raw `read()`: interleave your writes with the
  prompts instead of dumping one blob.
