# -*- coding: utf-8 -*-
import hashlib
from pathlib import Path
import sys
import zipfile

EXPECTED = {
    "Msg.xbb": "4b6002f69d4b39ee63834fe16e88e24ad305708f33a06578f47939c9d3a6715e",
    "DataText.xbb": "0205ed487d4f29e6be61996f7c72174bf806ccdcb4a4ca1a1334ce42bba5b0e1",
    "Font/mainfont.bffnt": "3fc950767ad7e93aff853a9426b7bd9f76ad02fcba410ac86fca599fda1c5521",
    "Font/subfont.bffnt": "3fc950767ad7e93aff853a9426b7bd9f76ad02fcba410ac86fca599fda1c5521",
    "Layout/ListSelect.arc": "413429d9121912596186c35f2119bfb0b1424dc23c41310e7eed5ab610ed18e2",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


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
    files = [
        p for p in root.rglob("*")
        if p.is_file() and p.name not in skip_names and "__MACOSX" not in p.parts
    ]
    files.sort(key=lambda p: str(p.relative_to(root)).lower())

    out.parent.mkdir(parents=True, exist_ok=True)
    manifest = out.parent / "PAYLOAD_MANIFEST.txt"
    lines = [
        "Trio Runtime10 RomFS Payload Audit",
        "==================================",
        f"ROOT={root}",
        f"FILE_COUNT={len(files)}",
        "",
        "KEY FILE VERIFICATION",
        "---------------------",
    ]

    for rel, expected in EXPECTED.items():
        p = root / Path(rel)
        if not p.is_file():
            lines.append(f"{rel}\tMISSING\texpected={expected}")
            print(f"AUDIT {rel}: MISSING expected={expected}")
            continue
        actual = sha256_file(p)
        status = "MATCH" if actual.lower() == expected.lower() else "MISMATCH"
        lines.append(
            f"{rel}\t{status}\tsize={p.stat().st_size}\tsha256={actual}\texpected={expected}"
        )
        print(f"AUDIT {rel}: {status} size={p.stat().st_size} sha256={actual} expected={expected}")

    lines += ["", "ALL PAYLOAD FILES", "-----------------"]
    for p in files:
        rel = p.relative_to(root).as_posix()
        digest = sha256_file(p)
        line = f"{rel}\tsize={p.stat().st_size}\tsha256={digest}"
        lines.append(line)
        print("PAYLOAD_FILE " + line)

    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in files:
            zf.write(p, p.relative_to(root).as_posix())

    h = hashlib.sha256(out.read_bytes()).hexdigest()
    print(f"payload files={len(files)} zip={out} size={out.stat().st_size} sha256={h}")
    print(f"payload manifest={manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
