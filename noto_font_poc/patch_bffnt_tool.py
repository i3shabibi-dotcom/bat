#!/usr/bin/env python3
from pathlib import Path

p = Path(__file__).resolve().parent / "vendor" / "bffnt.py"
s = p.read_text(encoding="utf-8")

patches = []

old = "        self.tglp = {\n            'size': section_size,\n            'glyph': {"
new = "        self.tglp = {\n            'size': section_size,\n            'maxCharWidth': max_char_width,\n            'glyph': {"
patches.append(("retain TGLP maxCharWidth", old, new))

old = """            file_.write(struct.pack('%sH' % self.order, len(cmap['entries'])))
            position += 2

            if cmap['type'] == MAPPING_DIRECT:
                file_.write(struct.pack('%sH' % self.order, cmap['indexOffset']))
                position += 2
            elif cmap['type'] == MAPPING_TABLE:
                for index in cmap['indexTable']:
                    file_.write(struct.pack('%sH' % self.order, index))
                    position += 2
            elif cmap['type'] == MAPPING_SCAN:
                keys = list(cmap['entries'].keys())
                keys.sort()
                for code in keys:
                    index = cmap['entries'][code]
                    file_.write(struct.pack('%s2H' % self.order, ord(code), index))
                    position += 4
"""
new = """            if cmap['type'] == MAPPING_DIRECT:
                file_.write(struct.pack('%sH' % self.order, cmap['indexOffset']))
                position += 2
            elif cmap['type'] == MAPPING_TABLE:
                for index in cmap['indexTable']:
                    file_.write(struct.pack('%sH' % self.order, index))
                    position += 2
            elif cmap['type'] == MAPPING_SCAN:
                file_.write(struct.pack('%sH' % self.order, len(cmap['entries'])))
                position += 2
                keys = list(cmap['entries'].keys())
                keys.sort()
                for code in keys:
                    index = cmap['entries'][code]
                    file_.write(struct.pack('%s2H' % self.order, ord(code), index))
                    position += 4
"""
patches.append(("correct DIRECT/TABLE/SCAN CMAP payload writer", old, new))

old = """            b1 = (r4 << 4) | g4
            b2 = (b4 << 4) | a4
            return [b1, b2]
"""
new = """            b1 = (r4 << 4) | a4
            b2 = (b4 << 4) | g4
            return [b1, b2]
"""
patches.append(("correct 3DS RGBA4 writer RRRRAAAA/BBBBGGGG", old, new))

for description, old, new in patches:
    if old not in s:
        raise SystemExit(f"Required upstream block not found: {description}")
    s = s.replace(old, new, 1)
    print(f"PATCHED: {description}")

p.write_text(s, encoding="utf-8")
