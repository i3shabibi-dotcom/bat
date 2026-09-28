#!/usr/bin/env python3
from pathlib import Path

p = Path(__file__).resolve().parent / "build_poc.py"
s = p.read_text(encoding="utf-8")
old = '            cand_images[existing_si].paste(cell, (box[0], box[1]), cell)\n'
new = (
    '            # Replace the Arabic slot completely; do not alpha-blend Noto over old Zelda artwork.\n'
    '            cand_images[existing_si].paste((0, 0, 0, 0), box)\n'
    '            cand_images[existing_si].alpha_composite(cell, (box[0], box[1]))\n'
)
if old not in s:
    raise SystemExit("Expected glyph replacement line not found")
p.write_text(s.replace(old, new, 1), encoding="utf-8")
print("PATCHED: clear Arabic glyph cell before Noto compositing")
