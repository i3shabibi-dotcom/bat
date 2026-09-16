# -*- coding: utf-8 -*-
import hashlib
from pathlib import Path
import sys
import zipfile


def choose_root(root: Path) -> Path:
    entries = [p for p in root.iterdir() if p.name != "__MACOSX"]
    if len(entries) == 1 and entries[0].is_dir() and entries[0].name.lower() == "romfs":
        return entries[0]
    return root


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: python prepare_payload.py <extracted-dir> <romfs.zip>")
        return 2
    root = choose_root(Path(sys.argv[1]).resolve())
    out = Path(sys.argv[2]).resolve()
    anchors = [
        root / "Msg.xbb",
        root / "DataText.xbb",
        root / "Font" / "mainfont.bffnt",
        root / "Layout" / "ListSelect.arc",
    ]
    if not any(p.is_file() for p in anchors):
        raise SystemExit("payload does not look like Trio of Towns RomFS overlay")

    skip_names = {"Thumbs.db", ".DS_Store"}
    files = [p for p in root.rglob("*") if p.is_file() and p.name not in skip_names and "__MACOSX" not in p.parts]
    files.sort(key=lambda p: str(p.relative_to(root)).lower())
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in files:
            zf.write(p, p.relative_to(root).as_posix())

    h = hashlib.sha256(out.read_bytes()).hexdigest()
    print(f"payload files={len(files)} zip={out} size={out.stat().st_size} sha256={h}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
