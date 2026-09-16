# -*- coding: utf-8 -*-
"""Build an .ah3p package from an extracted RomFS overlay directory."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import zipfile

FORMAT_ID = "arabic-hesham-3ds-romfs-patch"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    if len(sys.argv) != 9:
        print("usage: make_patch.py <romfs-dir> <out.ah3p> <patch-id> <patch-name> <patch-version> <game-name> <source-size> <source-sha256>")
        return 2
    romfs = Path(sys.argv[1]).resolve()
    out = Path(sys.argv[2]).resolve()
    if not romfs.is_dir():
        raise SystemExit("romfs directory not found")
    files = sorted((p for p in romfs.rglob("*") if p.is_file()), key=lambda p: p.relative_to(romfs).as_posix().lower())
    if not files:
        raise SystemExit("romfs overlay is empty")
    manifest = {
        "format": FORMAT_ID,
        "format_version": 1,
        "target": "3ds_romfs_overlay",
        "patch_id": sys.argv[3],
        "patch_name": sys.argv[4],
        "patch_version": sys.argv[5],
        "author": "Arabic Hesham",
        "game": {"name": sys.argv[6]},
        "source": {"size": int(sys.argv[7]), "sha256": [sys.argv[8].lower()]},
        "output_suffix": "_Arabic_Hesham",
        "files": {p.relative_to(romfs).as_posix(): sha256(p) for p in files},
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        zf.writestr("patch.json", json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"))
        for p in files:
            zf.write(p, "romfs/" + p.relative_to(romfs).as_posix())
    print(f"created {out} files={len(files)} size={out.stat().st_size} sha256={sha256(out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
