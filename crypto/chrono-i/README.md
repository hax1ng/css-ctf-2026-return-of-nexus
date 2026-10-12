# Chrono I

**Category:** Cryptography · **Points:** 25 · **Solves:** 552 · **Challenge ID:** 20

> We have intercepted a message and a Ciphertext, please help us crack the Ciphertext!

## Challenge

We are handed an intercepted message with a timestamp and a ciphertext, and told the flag is hidden inside:

```
Message:

2026/09/21 14:35:07 - "As always, The time is always the key to unlock it"

Ciphertext:

ESUITO{gwfvb_xejqnf_nimgt_b_whhrlv}

Flag Format: CSSCTF{...}
```

The flavour text ("The time is always the key") and the title (**Chrono**) both point at the same thing: the timestamp *is* the key.

## Initial analysis

The ciphertext already looks like a flag: six uppercase letters, braces, lowercase words separated by underscores. That shape is preserved, so this is a monoalphabetic-style substitution that leaves punctuation untouched — a Caesar/Vigenère variant.

The known-plaintext anchor is the flag prefix. The ciphertext starts `ESUITO`, and we know the plaintext must start `CSSCTF`. Lining the two up letter by letter:

| cipher | E | S | U | I | T | O |
|--------|---|---|---|---|---|---|
| plain  | C | S | S | C | T | F |
| shift  | 2 | 0 | 2 | 6 | 0 | 9 |

The shifts are exactly `2, 0, 2, 6, 0, 9` — the leading digits of the timestamp `2026/09/21 14:35:07` with the separators removed: **`20260921143507`**.

## Vulnerability / core concept

This is a periodic Caesar cipher keyed by the timestamp digits. The key string is the timestamp stripped of all non-digits:

```
20260921143507
```

For each **alphabetic** character of the ciphertext, subtract the next key digit modulo 26 (preserving case). Non-letters — braces and underscores — are copied straight through and, crucially, **do not consume a key digit**. The key index only advances on letters, and the 14-digit key simply repeats.

## Exploitation

The full recovery is in [`solve.py`](solve.py). The core is a dozen lines:

```python
ciphertext = "ESUITO{gwfvb_xejqnf_nimgt_b_whhrlv}"
key = "20260921143507"

def decrypt(text, digits):
    output, digit_index = [], 0
    for char in text:
        if char.isascii() and char.isalpha():
            base = ord("A" if char.isupper() else "a")
            shift = int(digits[digit_index % len(digits)])
            output.append(chr(base + (ord(char) - base - shift) % 26))
            digit_index += 1
        else:
            output.append(char)   # punctuation: copied, key not advanced
    return "".join(output)
```

Running it:

```console
$ python3 solve.py
CSSCTF{every_second_hides_a_secret}
```

The prefix resolves to `CSSCTF` and the body to the grammatical phrase `every_second_hides_a_secret`, confirming the key choice. (Advancing the key on punctuation as well produces garbage, which rules out that variant.)

## Flag

```
CSSCTF{every_second_hides_a_secret}
```

## Key takeaways

- When the prompt says the *time* is the key, treat the timestamp digits literally as a repeating numeric shift key.
- A known flag prefix (`CSSCTF`) is a free six-character known-plaintext crib — align it with the ciphertext to read the shifts straight off.
- Preserving braces/underscores and only advancing the key on letters is the detail that makes the plaintext fall out cleanly.
