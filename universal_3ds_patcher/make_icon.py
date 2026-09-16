from PIL import Image, ImageDraw, ImageFont

size = 256
img = Image.new("RGBA", (size, size), (23, 23, 23, 255))
d = ImageDraw.Draw(img)
d.rounded_rectangle((18, 18, 238, 238), radius=42, fill=(243, 167, 18, 255))
d.rounded_rectangle((42, 42, 214, 214), radius=30, fill=(23, 23, 23, 255))
try:
    font = ImageFont.truetype("arialbd.ttf", 112)
except Exception:
    font = ImageFont.load_default()
text = "H3"
b = d.textbbox((0, 0), text, font=font)
w, h = b[2] - b[0], b[3] - b[1]
d.text(((size - w) / 2, (size - h) / 2 - 8), text, font=font, fill=(243, 167, 18, 255))
img.save("icon.ico", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
print("created icon.ico")
