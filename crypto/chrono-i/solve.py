#!/usr/bin/env python3
"""Solve Chrono I using the timestamp digits as periodic Caesar shifts."""

ciphertext = "ESUITO{gwfvb_xejqnf_nimgt_b_whhrlv}"
key = "20260921143507"


def decrypt(text: str, digits: str) -> str:
    output = []
    digit_index = 0
    for char in text:
        if char.isascii() and char.isalpha():
            base = ord("A" if char.isupper() else "a")
            shift = int(digits[digit_index % len(digits)])
            output.append(chr(base + (ord(char) - base - shift) % 26))
            digit_index += 1
        else:
            output.append(char)
    return "".join(output)


if __name__ == "__main__":
    print(decrypt(ciphertext, key))
