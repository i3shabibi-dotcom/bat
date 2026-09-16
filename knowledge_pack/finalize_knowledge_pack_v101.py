from __future__ import annotations

import hashlib
import json
import shutil
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACK = ROOT / "dist" / "3DS_ARABIC_LOCALIZATION_KNOWLEDGE_PACK"
LEGACY = PACK / "13_REFERENCE_FILES" / "legacy_verified_tools"

UPSTREAM_REPO = "mirusu400/Story-of-seasons-Trio-of-Towns-Fan-Translation"
UPSTREAM_COMMIT = "66e01a9f78474bbf0cdb41aeb1605725e68e90ff"
RAW_BASE = f"https://raw.githubusercontent.com/{UPSTREAM_REPO}/{UPSTREAM_COMMIT}/"

# Git blob SHA-1 values from the exact reviewed upstream commit tree.
FILES = {
    "tool_xbb.py": "0e97f6f26b3576df85ae792c065c76c192d125ce",
    "convert_format.py": "bc3cfd6de0393fd939b919ba844a358d467b9b75",
    "repack_xbb.py": "3b5b794991d94b6e9c6e2c73be1053221759fb3d",
    "extract.py": "edbbce1fdec0246f8e0427af1e03f732c9c71831",
    "import.py": "999302d4cc90082b9dcdaf61f7437c2ecb82e30f",
    "STRUCT.md": "fcf9005d11cc85857e0cbaead8b81fb2bb186d64",
    "tool_font.py": "d5b64b01ef364fb946faaafc5666b4b2c92580e8",
    "tool_gfx.py": "de3bf408efe6bd5c6370fa4fd874ba700ab1bab2",
    "tools/bffnt.py": "f7649131635351c5a718920f76897ce24de35ac8",
    "tools/bflim.py": "a58ad073c14795dc200f5096afd8cc2b0376847a",
    "tools/sarc.py": "5edb9d2769df1ebef81f58c0ed710eaa7465ca94",
    "requirements-upstream.txt": "f113755ca95b509b737982103fd8ee73d5316b49",
    "README-upstream.md": "a2e2414f2cde475edec8c736cea1a899eed29789",
}

SOURCE_PATHS = {
    "requirements-upstream.txt": "requirements.txt",
    "README-upstream.md": "README.md",
}


def git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def download_verified() -> list[dict]:
    LEGACY.mkdir(parents=True, exist_ok=True)
    records = []
    for dest_rel, expected_blob in FILES.items():
        src_rel = SOURCE_PATHS.get(dest_rel, dest_rel)
        url = RAW_BASE + src_rel
        with urllib.request.urlopen(url, timeout=60) as response:
            data = response.read()
        actual_blob = git_blob_sha1(data)
        if actual_blob != expected_blob:
            raise RuntimeError(
                f"Upstream blob mismatch for {src_rel}: {actual_blob} != {expected_blob}"
            )
        dest = LEGACY / dest_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        records.append(
            {
                "file": dest_rel,
                "upstream_path": src_rel,
                "git_blob_sha1": actual_blob,
                "sha256": sha256(data),
                "size": len(data),
            }
        )
    return records


def write_reference_readme(records: list[dict]) -> None:
    text = f"""# Legacy Verified Tools\n\n**REFERENCE ONLY — REVALIDATE FOR NEW GAME**\n\nThese files are exact copies recovered from the upstream repository and commit that were actually audited during the completed Trio of Towns project. They are preserved as historical working references; they are not assumptions about a new game.\n\n- Repository: `{UPSTREAM_REPO}`\n- Reviewed commit: `{UPSTREAM_COMMIT}`\n- Commit purpose recorded by the completed project: `update font tool, for generic use`\n\n## Tool roles\n\n- `tool_xbb.py`: XBB unpacking plus PAPA-to-JSON parsing used as part of the verified XBB/PAPA workflow.\n- `convert_format.py`: converts extracted PAPA JSON to the formatted translation structure used by the repacker workflow.\n- `repack_xbb.py`: PAPA rebuild plus XBB repacking; the completed project verified a no-translation round-trip against the target Msg.xbb.\n- `extract.py` / `import.py`: original repository extraction/import helpers retained for reference.\n- `tool_font.py` + `tools/bffnt.py`: BFFNT extraction/build/glyph tooling from the reviewed final upstream commit.\n- `tool_gfx.py` + `tools/bflim.py` + `tools/sarc.py`: graphics/archive helpers retained because the completed project later required layout/texture work.\n- `STRUCT.md`: upstream structural notes. It is game/version-specific documentation and MUST NOT override inspection of a new game's actual files.\n- `requirements-upstream.txt`: the original dependency ranges from the reviewed upstream commit.\n\n## Important limitations\n\nThe completed project reports also reference project-created scripts such as `extract_3ds.py`, `audit_roundtrip.py`, and `token_validator.py`. Exact historical source copies of those project-created files were not recoverable from the currently accessible final repository/artifacts during this final review, so they have NOT been synthesized or falsely labeled as originals. The Knowledge Pack's reusable equivalents remain the supported transfer material.\n\nDo not copy game assets, Title IDs, offsets, font data, or XBB/PAPA assumptions into a new project without validation.\n\n## Integrity\n\n`LEGACY_VERIFIED_TOOLS_MANIFEST.json` records the exact Git blob SHA-1 and ordinary SHA-256 of each recovered reference file.\n"""
    (LEGACY / "README.md").write_text(text, encoding="utf-8")
    manifest = {
        "status": "REFERENCE ONLY — REVALIDATE FOR NEW GAME",
        "repository": UPSTREAM_REPO,
        "commit": UPSTREAM_COMMIT,
        "files": records,
    }
    (LEGACY / "LEGACY_VERIFIED_TOOLS_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def remove_python_cache() -> tuple[int, int]:
    cache_dirs = sorted(PACK.rglob("__pycache__"), key=lambda p: len(p.parts), reverse=True)
    pyc_files = list(PACK.rglob("*.pyc"))
    removed_dirs = 0
    removed_pyc = 0
    for p in pyc_files:
        if p.exists():
            p.unlink()
            removed_pyc += 1
    for d in cache_dirs:
        if d.exists():
            shutil.rmtree(d)
            removed_dirs += 1
    return removed_dirs, removed_pyc


def main() -> int:
    if not PACK.is_dir():
        raise SystemExit(f"Knowledge Pack directory missing: {PACK}")
    records = download_verified()
    write_reference_readme(records)
    dirs, pycs = remove_python_cache()
    print(f"legacy_verified_files={len(records)}")
    print(f"removed_pycache_dirs={dirs}")
    print(f"removed_pyc_files={pycs}")
    print(f"pack_root={PACK}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
