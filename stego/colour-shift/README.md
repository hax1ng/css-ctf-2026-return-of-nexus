# Colour Shift

**Category:** Steganography · **Points:** 45 · **Solves:** 434 · **Challenge ID:** 17

> In 1666 Isaac Newton split light into their compositve wavelengths. Can you?

## Challenge

In 1666 Isaac Newton split light into their compositve wavelengths. Can you?

Flag format: `CSSCTF{...}`

Attachment:

- `colorshiftctf.bmp` — a 599 x 602, 24-bit RGB Windows bitmap depicting a prism
  splitting a beam of white light into a rainbow.

## Initial analysis

```
$ file colorshiftctf.bmp
colorshiftctf.bmp: PC bitmap, Windows 98/2000 and newer format, 599 x 602 x 24, cbSize 1083738, bits offset 138
```

A plain 24-bit BMP with no trailing data to carve — `binwalk`/`strings` turn up
nothing useful, and bit-plane extraction on the combined image reveals no
separate payload. The image content is the puzzle, not a wrapped file.

The prompt is the whole hint: Newton used a prism to **split light into its
component wavelengths**. In a digital image the "wavelengths" are the red,
green, and blue colour channels. The move is to split the picture into those
channels and look at each one on its own.

## Vulnerability / core concept

Classic colour-channel steganography. A faint block of uppercase text was
overlaid on the artwork and then the image's channels were manipulated so the
text all but disappears in the full-colour render but survives in a single
channel. Here the overlaid letters are darkest in the **red** channel, down in
the lower-left of the frame (roughly `y = 412–435`). Pulling the red channel out
and boosting its brightness makes the hidden phrase pop.

## Exploitation

The committed `solve.py` does the whole thing with Pillow:

1. Load the BMP and grab only the red channel (`Image.getchannel("R")`), saving
   it as `red_channel.png`.
2. Crop the lower-left strip where the letters live (`y = 390–480`).
3. Brighten that crop 5x and upscale it so the text is unambiguous, writing
   `hidden_text.png`.

```python
from PIL import Image, ImageEnhance

im = Image.open("colorshiftctf.bmp").convert("RGB")
red = im.getchannel("R")
red.save("red_channel.png")

crop = red.crop((0, 390, im.width, 480))
crop = ImageEnhance.Brightness(crop).enhance(5)
crop.resize((im.width * 2, 180)).save("hidden_text.png")
```

Run it from this directory:

```bash
python3 solve.py
```

`hidden_text.png` then clearly reads the flag text. Note the phrase inside the
braces has a **literal space** between the two words, not an underscore.

## Flag

```
CSSCTF{SHINE ON}
```

## Key takeaways

- "Split light into wavelengths" is a direct nudge toward separating an image's
  RGB colour channels — one of the first things to try on any colourful stego image.
- Overlaid text that is invisible in the composite can be obvious in a single
  channel; isolate R, G, and B and inspect each one.
- Watch the exact characters: the flag contains a real space, which is easy to
  misread as an underscore.
