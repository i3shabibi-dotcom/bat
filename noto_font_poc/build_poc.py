#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import os
import shutil
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import freetype
import numpy as np
import uharfbuzz as hb
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
VENDOR_BFFNT = ROOT / "vendor" / "bffnt.py"
BASELINE_ROOT = ROOT / "baseline_romfs"
FONT_PATH = ROOT / "input" / "NotoSansArabicUI-Regular.ttf"
OUT = ROOT / "out" / "LOC-NOTO-ARABIC-FONT-POC-011"
REPORTS = OUT / "reports"
PREVIEWS = OUT / "previews"
ROMFS_FONT = OUT / "romfs" / "Font"
WORK = ROOT / "work"

EXPECTED_FONT_SIZE = 274_752
EXPECTED_RUNTIME10_FONT_SHA256 = "3fc950767ad7e93aff853a9426b7bd9f76ad02fcba410ac86fca599fda1c5521"
EXPECTED_LISTSELECT_SHA256 = "413429d9121912596186c35f2119bfb0b1424dc23c41310e7eed5ab610ed18e2"
EXPECTED_MSG_SHA256 = "4b6002f69d4b39ee63834fe16e88e24ad305708f33a06578f47939c9d3a6715e"
EXPECTED_DATATEXT_SHA256 = "0205ed487d4f29e6be61996f7c72174bf806ccdcb4a4ca1a1334ce42bba5b0e1"

ARABIC_RANGES = (
    (0x0600, 0x06FF),
    (0x0750, 0x077F),
    (0x0870, 0x089F),
    (0x08A0, 0x08FF),
    (0xFB50, 0xFDFF),
    (0xFE70, 0xFEFF),
)

CELL_W = 14
CELL_H = 15
BASELINE_Y = 11
SOURCE_PIXEL_SIZE = 13
OVERSAMPLE = 4


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_dirs():
    if OUT.exists():
        shutil.rmtree(OUT)
    if WORK.exists():
        shutil.rmtree(WORK)
    for p in (REPORTS, PREVIEWS, ROMFS_FONT, WORK):
        p.mkdir(parents=True, exist_ok=True)


def load_bffnt_module():
    spec = importlib.util.spec_from_file_location("runtime10_bffnt", VENDOR_BFFNT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {VENDOR_BFFNT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def find_one(name: str) -> Path:
    hits = list(BASELINE_ROOT.rglob(name))
    if not hits:
        raise FileNotFoundError(f"Missing baseline file: {name}")
    preferred = [p for p in hits if "Font" in p.parts] if name.endswith(".bffnt") else hits
    return sorted(preferred or hits, key=lambda p: (len(p.parts), str(p)))[0]


def font_name(tt: TTFont, name_id: int) -> str:
    table = tt["name"]
    for platform, enc, lang in ((3, 1, 0x409), (3, 10, 0x409), (1, 0, 0)):
        rec = table.getName(name_id, platform, enc, lang)
        if rec:
            try:
                return rec.toUnicode()
            except Exception:
                return str(rec)
    for rec in table.names:
        if rec.nameID == name_id:
            try:
                return rec.toUnicode()
            except Exception:
                pass
    return ""


def unicode_cmap(tt: TTFont) -> dict[int, str]:
    result = {}
    for table in tt["cmap"].tables:
        if table.isUnicode():
            result.update(table.cmap)
    return result


def in_arabic_range(cp: int) -> bool:
    return any(a <= cp <= b for a, b in ARABIC_RANGES)


def glyph_map_from_bffnt(bffnt, module) -> dict[str, int]:
    result = {}
    for cmap in bffnt.cmap_sections:
        if cmap["type"] == module.MAPPING_DIRECT:
            for code in range(cmap["start"], cmap["end"] + 1):
                result[chr(code)] = code - cmap["start"] + cmap["indexOffset"]
        elif cmap["type"] == module.MAPPING_TABLE:
            for code in range(cmap["start"], cmap["end"] + 1):
                idx = cmap["indexTable"][code - cmap["start"]]
                if idx != 0xFFFF:
                    result[chr(code)] = idx
        elif cmap["type"] == module.MAPPING_SCAN:
            for ch, idx in cmap["entries"].items():
                result[ch] = idx
    return result


def widths_from_bffnt(bffnt) -> dict[int, dict]:
    result = {}
    for cwdh in bffnt.cwdh_sections:
        for idx in range(cwdh["start"], cwdh["end"] + 1):
            result[idx] = dict(cwdh["data"][idx - cwdh["start"]])
    return result


def cmap_architecture(bffnt) -> list[dict]:
    out = []
    for c in bffnt.cmap_sections:
        item = {"type": c["type"], "start": c["start"], "end": c["end"]}
        if "indexOffset" in c:
            item["indexOffset"] = c["indexOffset"]
        if "indexTable" in c:
            item["indexTable"] = list(c["indexTable"])
        if "entries" in c:
            item["entries"] = sorted((ord(k), int(v)) for k, v in c["entries"].items())
        out.append(item)
    return out


def cwdh_architecture(bffnt) -> list[dict]:
    out = []
    for c in bffnt.cwdh_sections:
        out.append({
            "start": c["start"],
            "end": c["end"],
            "data": [dict(x) for x in c["data"]],
        })
    return out


def sheet_images(bffnt) -> list[Image.Image]:
    images = []
    for sheet in bffnt.tglp["sheets"]:
        img = Image.new("RGBA", (sheet["width"], sheet["height"]))
        img.putdata([tuple(px) for px in sheet["data"]])
        images.append(img)
    return images


def glyph_rect(index: int, bffnt):
    sheet = bffnt.tglp["sheet"]
    cols = sheet["cols"]
    rows = sheet["rows"]
    per = cols * rows
    stride_x = sheet["width"] // cols
    stride_y = sheet["height"] // rows
    sheet_idx = index // per
    slot = index % per
    x = (slot % cols) * stride_x
    y = (slot // cols) * stride_y
    return sheet_idx, (x, y, x + bffnt.tglp["glyph"]["width"], y + bffnt.tglp["glyph"]["height"])


def alpha_bbox(img: Image.Image):
    return img.getchannel("A").getbbox()


def modal_ink_rgb(images, target_indices, bffnt):
    colors = Counter()
    for idx in sorted(target_indices):
        si, box = glyph_rect(idx, bffnt)
        crop = images[si].crop(box)
        for r, g, b, a in crop.getdata():
            if a >= 32:
                colors[(r, g, b)] += 1
    return colors.most_common(1)[0][0] if colors else (255, 255, 255)


class DonorRenderer:
    def __init__(self, path: Path, pixel_size=SOURCE_PIXEL_SIZE, oversample=OVERSAMPLE):
        self.path = path
        self.bytes = path.read_bytes()
        self.tt = TTFont(str(path))
        self.cmap = unicode_cmap(self.tt)
        self.glyph_order = self.tt.getGlyphOrder()
        self.gid_by_name = {n: i for i, n in enumerate(self.glyph_order)}
        self.upem = self.tt["head"].unitsPerEm
        self.face = freetype.Face(str(path))
        self.pixel_size = pixel_size
        self.oversample = oversample
        self.face.set_pixel_sizes(0, pixel_size * oversample)
        hb_face = hb.Face(self.bytes)
        self.hb_font = hb.Font(hb_face)
        hb.ot_font_set_funcs(self.hb_font)
        self.hb_font.scale = (self.upem, self.upem)
        self.unit_to_px = (pixel_size * oversample) / self.upem

    def direct_gid(self, cp: int):
        name = self.cmap.get(cp)
        return self.gid_by_name.get(name) if name else None

    def shape(self, text: str):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.hb_font, buf, {"kern": True, "liga": True, "calt": True})
        return list(zip(buf.glyph_infos, buf.glyph_positions))

    def load_bitmap(self, gid: int):
        flags = freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_NORMAL
        self.face.load_glyph(gid, flags)
        slot = self.face.glyph
        bmp = slot.bitmap
        if bmp.rows == 0 or bmp.width == 0:
            arr = np.zeros((0, 0), dtype=np.uint8)
        else:
            pitch = abs(bmp.pitch)
            raw = np.array(bmp.buffer, dtype=np.uint8)
            if raw.size < bmp.rows * pitch:
                padded = np.zeros(bmp.rows * pitch, dtype=np.uint8)
                padded[:raw.size] = raw
                raw = padded
            arr = raw.reshape((bmp.rows, pitch))[:, :bmp.width]
        return arr, int(slot.bitmap_left), int(slot.bitmap_top)

    def render_gid_sequence(self, shaped):
        items = []
        pen_x = 0.0
        pen_y = 0.0
        for info, pos in shaped:
            gid = int(info.codepoint)
            arr, left, top = self.load_bitmap(gid)
            x = pen_x + pos.x_offset * self.unit_to_px + left
            y = -(pen_y + pos.y_offset * self.unit_to_px) - top
            if arr.size:
                items.append((arr, x, y, gid))
            pen_x += pos.x_advance * self.unit_to_px
            pen_y += pos.y_advance * self.unit_to_px
        if not items:
            return Image.new("L", (1, 1), 0), 0.0, [], []
        min_x = math.floor(min(x for arr, x, y, gid in items))
        min_y = math.floor(min(y for arr, x, y, gid in items))
        max_x = math.ceil(max(x + arr.shape[1] for arr, x, y, gid in items))
        max_y = math.ceil(max(y + arr.shape[0] for arr, x, y, gid in items))
        canvas = Image.new("L", (max(1, max_x - min_x), max(1, max_y - min_y)), 0)
        for arr, x, y, gid in items:
            glyph = Image.fromarray(arr, mode="L")
            canvas.paste(glyph, (round(x - min_x), round(y - min_y)), glyph)
        baseline_in = -min_y
        gids = [gid for arr, x, y, gid in items]
        return canvas, baseline_in, gids, items

    def render_direct(self, cp: int):
        gid = self.direct_gid(cp)
        if gid is None:
            return None
        arr, left, top = self.load_bitmap(gid)
        if arr.size == 0:
            return Image.new("L", (1, 1), 0), 0.0, [gid]
        img = Image.fromarray(arr, mode="L")
        baseline_in = top
        return img, baseline_in, [gid]

    def render_shaped_text(self, text: str):
        shaped = self.shape(text)
        img, baseline_in, gids, _items = self.render_gid_sequence(shaped)
        return img, baseline_in, gids


def presentation_decomposition(cp: int):
    dec = unicodedata.decomposition(chr(cp))
    if not dec:
        return None, []
    parts = dec.split()
    tag = None
    if parts and parts[0].startswith("<"):
        tag = parts.pop(0)[1:-1]
    cps = []
    for p in parts:
        try:
            cps.append(int(p, 16))
        except ValueError:
            pass
    return tag, cps


def context_for_form(tag, cps):
    text = "".join(chr(cp) for cp in cps)
    zwj = "\u200d"
    if tag == "initial":
        return text + zwj
    if tag == "final":
        return zwj + text
    if tag == "medial":
        return zwj + text + zwj
    return text


def classify_and_render(cp: int, renderer: DonorRenderer, preserve_policy=False):
    ch = chr(cp)
    cat = unicodedata.category(ch)
    if preserve_policy or cat.startswith("P") or cat == "Nd":
        return "KEEP_EXISTING", None, [], "Preserved by punctuation/numeric policy"

    direct = renderer.render_direct(cp)
    if direct is not None:
        img, baseline, gids = direct
        return "DIRECT_TTF", (img, baseline), gids, "Direct Unicode cmap glyph"

    tag, cps = presentation_decomposition(cp)
    if cps:
        context = context_for_form(tag, cps)
        img, baseline, gids = renderer.render_shaped_text(context)
        visible_gids = [g for g in gids if g != 0]
        if visible_gids and alpha_bbox(img):
            status = "GSUB_DERIVED" if len(visible_gids) == 1 else "COMPOSITE"
            return status, (img, baseline), visible_gids, f"Unicode decomposition <{tag or 'none'}> + OpenType shaping"

    return "MISSING", None, [], "No direct cmap glyph and no renderable GSUB/composite derivation"


def fit_mask_to_cell(mask: Image.Image, baseline_in: float, safe_box, ink_rgb):
    if mask.getbbox() is None:
        return Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0)), 1.0

    bbox = mask.getbbox()
    mask = mask.crop(bbox)
    baseline_in = baseline_in - bbox[1]

    sx0, sx1 = safe_box
    allowed_w = max(1, sx1 - sx0)
    top_extent = max(0.0, baseline_in)
    bottom_extent = max(0.0, mask.height - baseline_in)
    max_top = max(1, BASELINE_Y)
    max_bottom = max(1, CELL_H - BASELINE_Y)
    scale = min(
        1.0,
        allowed_w * OVERSAMPLE / max(1, mask.width),
        max_top * OVERSAMPLE / max(1.0, top_extent),
        max_bottom * OVERSAMPLE / max(1.0, bottom_extent),
    )
    new_w = max(1, int(round(mask.width * scale / OVERSAMPLE)))
    new_h = max(1, int(round(mask.height * scale / OVERSAMPLE)))
    logical = mask.resize((new_w, new_h), Image.Resampling.LANCZOS)
    logical_baseline = baseline_in * scale / OVERSAMPLE

    x = sx0 + max(0, (allowed_w - new_w) // 2)
    y = int(round(BASELINE_Y - logical_baseline))
    y = min(max(y, 0), max(0, CELL_H - new_h))

    rgba = Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0))
    glyph_rgba = Image.new("RGBA", logical.size, (*ink_rgb, 0))
    glyph_rgba.putalpha(logical)
    rgba.alpha_composite(glyph_rgba, (x, y))
    return rgba, scale


def select_safe_box(existing: Image.Image, width_metric: dict):
    bbox = alpha_bbox(existing)
    glyph_w = int(width_metric.get("glyph", 0))
    if bbox:
        x0 = max(0, bbox[0] - 1)
        x1 = min(CELL_W, max(bbox[2] + 1, x0 + max(1, glyph_w)))
    elif glyph_w > 0:
        x0, x1 = 0, min(CELL_W, glyph_w)
    else:
        x0, x1 = 0, CELL_W
    if x1 <= x0:
        x0, x1 = 0, CELL_W
    return x0, x1


def render_bffnt_text(text: str, glyph_map, widths, images, bffnt, line_width=320):
    # text must already be in visual order / presentation-form order.
    placements = []
    x = 0
    for ch in text:
        idx = glyph_map.get(ch)
        if idx is None:
            x += 5
            continue
        w = widths.get(idx, {"left": 0, "glyph": CELL_W, "char": CELL_W})
        si, box = glyph_rect(idx, bffnt)
        cell = images[si].crop(box)
        placements.append((x + int(w.get("left", 0)), cell))
        x += max(0, int(w.get("char", CELL_W)))
    canvas = Image.new("RGBA", (max(1, min(line_width, x + 2)), CELL_H + 2), (0, 0, 0, 0))
    for px, cell in placements:
        if px < canvas.width:
            canvas.alpha_composite(cell, (px, 1))
    return canvas


def make_atlas(rows, images, bffnt, out_path: Path, title: str):
    scale = 6
    label_font = ImageFont.load_default()
    row_h = max(CELL_H * scale + 4, 94)
    col_w = 250
    ncols = 4
    nrows = math.ceil(len(rows) / ncols)
    canvas = Image.new("RGB", (ncols * col_w, 30 + nrows * row_h), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((8, 8), title, fill="black", font=label_font)
    for i, r in enumerate(rows):
        col = i % ncols
        rr = i // ncols
        x = col * col_w + 8
        y = 30 + rr * row_h
        cp = int(r["codepoint"], 16)
        idx = int(r["glyph_index"])
        si, box = glyph_rect(idx, bffnt)
        glyph = images[si].crop(box).resize((CELL_W * scale, CELL_H * scale), Image.Resampling.NEAREST)
        checker = Image.new("RGB", glyph.size, (236, 236, 236))
        checker.paste(glyph.convert("RGBA"), (0, 0), glyph)
        canvas.paste(checker, (x, y))
        label = f"U+{cp:04X} idx={idx} {r['status']}"
        draw.text((x + CELL_W * scale + 5, y + 3), label, fill="black", font=label_font)
        name = unicodedata.name(chr(cp), "UNNAMED")
        draw.text((x + CELL_W * scale + 5, y + 18), name[:26], fill="black", font=label_font)
    canvas.save(out_path)


def make_comparison(rows, base_images, cand_images, bffnt, out_path: Path):
    scale = 5
    label_font = ImageFont.load_default()
    row_h = CELL_H * scale + 8
    width = 620
    height = 28 + len(rows) * row_h
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((8, 8), "Runtime10 (left) vs Noto donor candidate (right)", fill="black", font=label_font)
    for i, r in enumerate(rows):
        y = 28 + i * row_h
        cp = int(r["codepoint"], 16)
        idx = int(r["glyph_index"])
        si, box = glyph_rect(idx, bffnt)
        a = base_images[si].crop(box).resize((CELL_W * scale, CELL_H * scale), Image.Resampling.NEAREST)
        b = cand_images[si].crop(box).resize((CELL_W * scale, CELL_H * scale), Image.Resampling.NEAREST)
        canvas.paste(a, (8, y), a)
        canvas.paste(b, (90, y), b)
        draw.text((175, y + 4), f"U+{cp:04X} {r['status']} {unicodedata.name(chr(cp),'')[:42]}", fill="black", font=label_font)
    canvas.save(out_path)


def reshaped_visual(text: str):
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        return get_display(arabic_reshaper.reshape(text))
    except Exception:
        return text


def make_native_sample(glyph_map, widths, base_images, cand_images, bffnt, out_path: Path):
    samples = [
        "ج ح خ  ش س  ي ى  ق ف",
        "ء أ إ  لا لأ لإ لآ",
        "ك ک  کک  جديد",
        "مزرعتك جميلة 123 ABC",
    ]
    canvas = Image.new("RGBA", (400, 170), (255, 255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    label_font = ImageFont.load_default()
    y = 4
    for logical in samples:
        visual = reshaped_visual(logical)
        draw.text((2, y), "R10", fill="black", font=label_font)
        old = render_bffnt_text(visual, glyph_map, widths, base_images, bffnt, line_width=350)
        canvas.alpha_composite(old, (32, y))
        y += 19
        draw.text((2, y), "Noto", fill="black", font=label_font)
        new = render_bffnt_text(visual, glyph_map, widths, cand_images, bffnt, line_width=350)
        canvas.alpha_composite(new, (32, y))
        y += 22
    canvas.save(out_path)


def write_csv(path, rows, fieldnames):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def special_case_report(mapping_rows):
    wanted = [0x0621, 0xFB90] + list(range(0xFE70, 0xFE80)) + list(range(0xFEF5, 0xFEFD))
    by_cp = {int(r["codepoint"], 16): r for r in mapping_rows}
    return {
        f"U+{cp:04X}": by_cp.get(cp, {"status": "NOT_IN_TRIO_CMAP"})
        for cp in wanted
    }


def main():
    ensure_dirs()
    if FONT_PATH.stat().st_size != EXPECTED_FONT_SIZE:
        raise RuntimeError(f"Donor size mismatch: {FONT_PATH.stat().st_size} != {EXPECTED_FONT_SIZE}")

    module = load_bffnt_module()
    mainfont = find_one("mainfont.bffnt")
    subfont = find_one("subfont.bffnt")
    listselect = find_one("ListSelect.arc")
    msg = find_one("Msg.xbb")
    datatext = find_one("DataText.xbb")

    baseline_hashes = {
        "mainfont.bffnt": sha256(mainfont),
        "subfont.bffnt": sha256(subfont),
        "ListSelect.arc": sha256(listselect),
        "Msg.xbb": sha256(msg),
        "DataText.xbb": sha256(datatext),
    }
    if baseline_hashes["mainfont.bffnt"] != EXPECTED_RUNTIME10_FONT_SHA256:
        raise RuntimeError(f"Runtime10 mainfont baseline hash mismatch: {baseline_hashes['mainfont.bffnt']}")
    if baseline_hashes["subfont.bffnt"] != EXPECTED_RUNTIME10_FONT_SHA256:
        raise RuntimeError(f"Runtime10 subfont baseline hash mismatch: {baseline_hashes['subfont.bffnt']}")
    if baseline_hashes["ListSelect.arc"] != EXPECTED_LISTSELECT_SHA256:
        raise RuntimeError(f"Runtime10 ListSelect baseline hash mismatch: {baseline_hashes['ListSelect.arc']}")
    if baseline_hashes["Msg.xbb"] != EXPECTED_MSG_SHA256:
        raise RuntimeError(f"Msg baseline hash mismatch: {baseline_hashes['Msg.xbb']}")
    if baseline_hashes["DataText.xbb"] != EXPECTED_DATATEXT_SHA256:
        raise RuntimeError(f"DataText baseline hash mismatch: {baseline_hashes['DataText.xbb']}")

    b = module.Bffnt()
    b.read(str(mainfont))
    if b.invalid:
        raise RuntimeError("Baseline mainfont BFFNT parse failed")
    if (b.tglp["glyph"]["width"], b.tglp["glyph"]["height"], b.tglp["glyph"]["baseline"]) != (CELL_W, CELL_H, BASELINE_Y):
        raise RuntimeError(f"Unexpected Runtime10 cell metrics: {b.tglp['glyph']}")

    glyph_map = glyph_map_from_bffnt(b, module)
    widths = widths_from_bffnt(b)
    base_images = sheet_images(b)
    cand_images = [im.copy() for im in base_images]

    target_chars = {ch: idx for ch, idx in glyph_map.items() if in_arabic_range(ord(ch))}
    target_indices = set(target_chars.values())
    shared_non_arabic = {}
    for ch, idx in glyph_map.items():
        if idx in target_indices and not in_arabic_range(ord(ch)):
            shared_non_arabic.setdefault(idx, []).append(ch)

    ink_rgb = modal_ink_rgb(base_images, target_indices, b)
    renderer = DonorRenderer(FONT_PATH)

    tt = renderer.tt
    cmap = renderer.cmap
    hhea = tt["hhea"]
    audit = {
        "task": "LOC-NOTO-ARABIC-FONT-POC-011",
        "source_file": FONT_PATH.name,
        "source_size": FONT_PATH.stat().st_size,
        "sha256": sha256(FONT_PATH),
        "family": font_name(tt, 1),
        "subfamily": font_name(tt, 2),
        "full_name": font_name(tt, 4),
        "version": font_name(tt, 5),
        "unitsPerEm": tt["head"].unitsPerEm,
        "ascent": hhea.ascent,
        "descent": hhea.descent,
        "lineGap": hhea.lineGap,
        "unicode_cmap_count": len(cmap),
        "arabic_nominal_0600_06FF_count": sum(1 for cp in cmap if 0x0600 <= cp <= 0x06FF),
        "arabic_presentation_forms_A_FB50_FDFF_count": sum(1 for cp in cmap if 0xFB50 <= cp <= 0xFDFF),
        "arabic_presentation_forms_B_FE70_FEFF_count": sum(1 for cp in cmap if 0xFE70 <= cp <= 0xFEFF),
        "GSUB_available": "GSUB" in tt,
        "GPOS_available": "GPOS" in tt,
        "glyph_count": tt["maxp"].numGlyphs,
        "target_cell": {"width": CELL_W, "height": CELL_H, "baseline": BASELINE_Y},
        "source_pixel_size": SOURCE_PIXEL_SIZE,
        "oversample": OVERSAMPLE,
        "baseline_hashes": baseline_hashes,
        "baseline_identity": "Runtime10 hashes verified",
    }

    mapping_rows = []
    modified_indices = set()
    min_scale = 1.0
    for ch, idx in sorted(target_chars.items(), key=lambda kv: ord(kv[0])):
        cp = ord(ch)
        dec_tag, dec_cps = presentation_decomposition(cp)
        preserve = idx in shared_non_arabic
        status, rendered, gids, note = classify_and_render(cp, renderer, preserve_policy=preserve)
        existing_si, box = glyph_rect(idx, b)
        existing = base_images[existing_si].crop(box)
        width_metric = widths.get(idx, {"left": 0, "glyph": CELL_W, "char": CELL_W})
        scale = ""
        if preserve:
            status = "KEEP_EXISTING"
            note = "Glyph slot shared with non-Arabic mapping(s): " + ",".join(f"U+{ord(x):04X}" for x in shared_non_arabic[idx])
            rendered = None
        if rendered is not None and status in ("DIRECT_TTF", "GSUB_DERIVED", "COMPOSITE"):
            mask, baseline_in = rendered
            safe_box = select_safe_box(existing, width_metric)
            cell, sf = fit_mask_to_cell(mask, baseline_in, safe_box, ink_rgb)
            min_scale = min(min_scale, sf)
            scale = f"{sf:.4f}"
            cand_images[existing_si].paste(cell, (box[0], box[1]), cell)
            modified_indices.add(idx)
        mapping_rows.append({
            "codepoint": f"{cp:04X}",
            "character": ch,
            "unicode_name": unicodedata.name(ch, "UNNAMED"),
            "glyph_index": idx,
            "category": unicodedata.category(ch),
            "decomposition_tag": dec_tag or "",
            "decomposition": " ".join(f"U+{x:04X}" for x in dec_cps),
            "status": status,
            "donor_glyph_ids": " ".join(map(str, gids)),
            "fit_scale": scale,
            "cwdh_left": width_metric.get("left", ""),
            "cwdh_glyph": width_metric.get("glyph", ""),
            "cwdh_char": width_metric.get("char", ""),
            "note": note,
        })

    audit["required_trio_mapping_count"] = len(mapping_rows)
    audit["required_trio_direct_missing_count"] = sum(1 for r in mapping_rows if int(r["codepoint"],16) not in cmap)
    audit["status_counts"] = dict(Counter(r["status"] for r in mapping_rows))
    audit["required_forms_recoverable_through_GSUB_or_composite"] = sum(1 for r in mapping_rows if r["status"] in ("GSUB_DERIVED", "COMPOSITE"))
    audit["special_cases"] = special_case_report(mapping_rows)
    audit["ink_rgb_used"] = list(ink_rgb)
    audit["minimum_fit_scale"] = min_scale
    (REPORTS / "NOTO_FONT_SOURCE_AUDIT.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")

    write_csv(
        REPORTS / "NOTO_TRIO_MAPPING.csv",
        mapping_rows,
        ["codepoint","character","unicode_name","glyph_index","category","decomposition_tag","decomposition","status","donor_glyph_ids","fit_scale","cwdh_left","cwdh_glyph","cwdh_char","note"],
    )

    # Write candidate sheet PNGs under names required by bffnt.save().
    sheet_dir = WORK / "candidate_sheets"
    sheet_dir.mkdir(parents=True, exist_ok=True)
    for i, img in enumerate(cand_images):
        img.save(sheet_dir / f"mainfont_sheet{i}.png")

    old_cwd = Path.cwd()
    os.chdir(sheet_dir)
    try:
        b.save(str((ROMFS_FONT / "mainfont.bffnt").resolve()))
    finally:
        os.chdir(old_cwd)
    if b.invalid:
        raise RuntimeError("BFFNT save failed")
    shutil.copy2(ROMFS_FONT / "mainfont.bffnt", ROMFS_FONT / "subfont.bffnt")

    # Decode-back / structural QA.
    out_b = module.Bffnt()
    out_b.read(str(ROMFS_FONT / "mainfont.bffnt"))
    if out_b.invalid:
        raise RuntimeError("Candidate mainfont parse failed")
    out_images = sheet_images(out_b)
    out_map = glyph_map_from_bffnt(out_b, module)
    out_widths = widths_from_bffnt(out_b)

    non_arabic_changed = 0
    arabic_cell_mismatches_after_decode = 0
    for ch, idx in glyph_map.items():
        si0, box0 = glyph_rect(idx, b)
        si1, box1 = glyph_rect(idx, out_b)
        a = np.array(base_images[si0].crop(box0), dtype=np.uint8)
        c = np.array(cand_images[si0].crop(box0), dtype=np.uint8)
        d = np.array(out_images[si1].crop(box1), dtype=np.uint8)
        if not in_arabic_range(ord(ch)) and not np.array_equal(a, d):
            non_arabic_changed += 1
        if idx in modified_indices and not np.array_equal(c, d):
            arabic_cell_mismatches_after_decode += 1

    cwdh_delta_rows = []
    all_width_idxs = sorted(set(widths) | set(out_widths))
    for idx in all_width_idxs:
        before = widths.get(idx)
        after = out_widths.get(idx)
        if before != after:
            cwdh_delta_rows.append({"glyph_index": idx, "before": json.dumps(before, sort_keys=True), "after": json.dumps(after, sort_keys=True), "justification": "UNEXPECTED"})
    write_csv(REPORTS / "CWDH_DELTA.csv", cwdh_delta_rows, ["glyph_index","before","after","justification"])

    candidate_hash = sha256(ROMFS_FONT / "mainfont.bffnt")
    missing_rows = [r for r in mapping_rows if r["status"] == "MISSING"]
    qa = {
        "task": "LOC-NOTO-ARABIC-FONT-POC-011",
        "runtime_tested": False,
        "mainfont_rebuild": "PASS" if not out_b.invalid else "FAIL",
        "subfont_rebuild": "PASS",
        "mainfont_subfont_byte_identical": sha256(ROMFS_FONT / "mainfont.bffnt") == sha256(ROMFS_FONT / "subfont.bffnt"),
        "BFFNT_parse": "PASS" if not out_b.invalid else "FAIL",
        "decode_back": "PASS" if arabic_cell_mismatches_after_decode == 0 else "FAIL",
        "decode_back_modified_cell_mismatch_count": arabic_cell_mismatches_after_decode,
        "CMAP_architecture_preserved": cmap_architecture(b) == cmap_architecture(out_b),
        "CMAP_mapping_preserved": glyph_map == out_map,
        "CWDH_architecture_preserved": cwdh_architecture(b) == cwdh_architecture(out_b),
        "unexpected_CWDH_changes": len(cwdh_delta_rows),
        "non_Arabic_glyph_artwork_changed": non_arabic_changed,
        "Arabic_target_mapping_count": len(mapping_rows),
        "Arabic_modified_glyph_slots": len(modified_indices),
        "Arabic_missing_mappings": len(missing_rows),
        "Arabic_missing_codepoints": [f"U+{int(r['codepoint'],16):04X}" for r in missing_rows],
        "shaping_RTL": "UNCHANGED_BY_SCOPE",
        "wrapping": "UNCHANGED_BY_SCOPE",
        "Msg.xbb": "UNCHANGED_HASH_VERIFIED_BASELINE",
        "DataText.xbb": "UNCHANGED_HASH_VERIFIED_BASELINE",
        "Layout": "UNCHANGED_HASH_VERIFIED_RUNTIME10_LISTSELECT",
        "code.bin": "UNCHANGED_NOT_TOUCHED",
        "baseline_mainfont_sha256": baseline_hashes["mainfont.bffnt"],
        "candidate_mainfont_sha256": candidate_hash,
        "candidate_subfont_sha256": sha256(ROMFS_FONT / "subfont.bffnt"),
        "minimum_fit_scale": min_scale,
    }
    mandatory_pass = (
        qa["mainfont_rebuild"] == "PASS"
        and qa["mainfont_subfont_byte_identical"]
        and qa["BFFNT_parse"] == "PASS"
        and qa["decode_back"] == "PASS"
        and qa["CMAP_architecture_preserved"]
        and qa["CMAP_mapping_preserved"]
        and qa["CWDH_architecture_preserved"]
        and qa["unexpected_CWDH_changes"] == 0
        and qa["non_Arabic_glyph_artwork_changed"] == 0
    )
    qa["static_QA_overall"] = "PASS" if mandatory_pass else "FAIL"
    (REPORTS / "NOTO_FONT_POC_QA.json").write_text(json.dumps(qa, indent=2, ensure_ascii=False), encoding="utf-8")

    # Previews.
    preview_rows = [r for r in mapping_rows if r["status"] in ("DIRECT_TTF","GSUB_DERIVED","COMPOSITE")]
    make_atlas(mapping_rows, out_images, out_b, PREVIEWS / "NOTO_ARABIC_ATLAS.png", "NotoSansArabicUI donor candidate — Trio 14x15 / baseline 11")
    make_comparison(preview_rows, base_images, out_images, out_b, PREVIEWS / "NOTO_VS_RUNTIME10.png")
    make_native_sample(glyph_map, widths, base_images, out_images, out_b, PREVIEWS / "NOTO_NATIVE_SAMPLE.png")

    readme = f"""# LOC-NOTO-ARABIC-FONT-POC-011\n\nهذه حزمة PoC خاصة بالخط فقط.\n\n- المصدر: `NotoSansArabicUI-Regular.ttf`\n- SHA-256 للمصدر المستخدم: `{audit['sha256']}`\n- Runtime10 baseline font SHA-256: `{baseline_hashes['mainfont.bffnt']}`\n- Candidate font SHA-256: `{candidate_hash}`\n- المقاس المستهدف: `14×15`\n- Baseline: `11`\n- shaping/RTL/wrapping/text: لم يتم تعديلها.\n- Msg.xbb / DataText.xbb / Layout / code.bin: لم يتم تعديلها.\n- Runtime: **NOT TESTED**.\n\nراجع صور `previews/` وتقارير `reports/` قبل السماح ببناء Runtime.\n"""
    (OUT / "README_AR.md").write_text(readme, encoding="utf-8")

    checksum_lines = []
    for p in sorted(x for x in OUT.rglob("*") if x.is_file() and x.name != "SHA256SUMS.txt"):
        checksum_lines.append(f"{sha256(p)}  {p.relative_to(OUT).as_posix()}")
    (OUT / "SHA256SUMS.txt").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")

    print(json.dumps({
        "static_QA": qa["static_QA_overall"],
        "source_sha256": audit["sha256"],
        "candidate_sha256": candidate_hash,
        "mapping_status_counts": audit["status_counts"],
        "missing": len(missing_rows),
        "out": str(OUT),
    }, ensure_ascii=False, indent=2))

    if not mandatory_pass:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
