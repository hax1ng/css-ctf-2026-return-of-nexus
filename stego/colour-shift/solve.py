from pathlib import Path
from PIL import Image, ImageEnhance


here = Path(__file__).resolve().parent
im = Image.open(here / "colorshiftctf.bmp").convert("RGB")
red = im.getchannel("R")
red.save(here / "red_channel.png")

# The dark overlaid letters are clearest in red, near the lower left.
crop = red.crop((0, 390, im.width, 480))
crop = ImageEnhance.Brightness(crop).enhance(5)
crop.resize((im.width * 2, 180)).save(here / "hidden_text.png")
