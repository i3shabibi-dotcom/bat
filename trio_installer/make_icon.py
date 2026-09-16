from PIL import Image, ImageDraw, ImageFont

SIZE = 256
img = Image.new("RGBA", (SIZE, SIZE), (23, 23, 23, 255))
d = ImageDraw.Draw(img)
amber = (243, 167, 18, 255)
# A simple branded H that does not depend on an external font file.
bar = 42
margin = 52
d.rounded_rectangle((margin, 42, margin + bar, 214), radius=12, fill=amber)
d.rounded_rectangle((SIZE - margin - bar, 42, SIZE - margin, 214), radius=12, fill=amber)
d.rounded_rectangle((margin, 107, SIZE - margin, 149), radius=12, fill=amber)
img.save("icon.ico", sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
print("created icon.ico")
