# -*- coding: utf-8 -*-
"""Generic Nintendo 3DS RomFS overlay patch engine.

Patch packages are ordinary ZIP files with extension .ah3p. They contain:
  patch.json
  romfs/<overlay files>

The selected source image is never modified in-place. The engine validates the
source against the hashes declared by the patch, rebuilds partition 0 with the
RomFS overlay, preserves every other NCSD partition that exists, and verifies
all patched files in the rebuilt output before reporting success.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

FORMAT_ID = "arabic-hesham-3ds-romfs-patch"
FORMAT_VERSION = 1
PROGRESS_CB = None
LAST_OUTPUT = None
LAST_OUTPUT_SHA256 = None
LAST_PATCH = None


def resource_path(rel: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


def _report(name: str, pct: float) -> None:
    if PROGRESS_CB:
        PROGRESS_CB(name, max(0, min(100, int(pct))))


def _sha256_file(path: str, cb=None) -> str:
    h = hashlib.sha256()
    size = os.path.getsize(path)
    done = 0
    with open(path, "rb") as f:
        while True:
            chunk = f.read(8 * 1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
            done += len(chunk)
            if cb and size:
                cb(done, size)
    return h.hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_member(name: str) -> bool:
    n = name.replace("\\", "/")
    p = Path(n)
    return not p.is_absolute() and ".." not in p.parts and not n.startswith("/")


def _load_manifest_dict(raw: dict) -> dict:
    if raw.get("format") != FORMAT_ID:
        raise RuntimeError("صيغة الباتش غير مدعومة.")
    if int(raw.get("format_version", 0)) != FORMAT_VERSION:
        raise RuntimeError("إصدار صيغة الباتش غير مدعوم.")
    if raw.get("target") != "3ds_romfs_overlay":
        raise RuntimeError("نوع هذا الباتش غير مدعوم بواسطة هذه الأداة.")

    game = raw.get("game") or {}
    source = raw.get("source") or {}
    files = raw.get("files") or {}
    hashes = source.get("sha256") or []
    if isinstance(hashes, str):
        hashes = [hashes]
    hashes = [str(x).lower() for x in hashes if str(x).strip()]
    if not hashes:
        raise RuntimeError("الباتش لا يحتوي SHA-256 معتمد للعبة الأصلية.")
    if not isinstance(files, dict) or not files:
        raise RuntimeError("الباتش لا يحتوي قائمة ملفات RomFS للتحقق.")

    normalized = {}
    for rel, digest in files.items():
        rel = str(rel).replace("\\", "/").lstrip("/")
        if not rel or not _safe_member(rel):
            raise RuntimeError("مسار غير آمن في قائمة ملفات الباتش: " + rel)
        digest = str(digest).lower()
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise RuntimeError("SHA-256 غير صالح لملف الباتش: " + rel)
        normalized[rel] = digest

    return {
        "format": FORMAT_ID,
        "format_version": FORMAT_VERSION,
        "target": "3ds_romfs_overlay",
        "patch_id": str(raw.get("patch_id") or "unnamed-patch"),
        "patch_name": str(raw.get("patch_name") or "3DS RomFS Patch"),
        "patch_version": str(raw.get("patch_version") or "1.0"),
        "author": str(raw.get("author") or ""),
        "game_name": str(game.get("name") or "Nintendo 3DS Game"),
        "title_id": str(game.get("title_id") or "").upper(),
        "source_sha256": hashes,
        "source_size": int(source.get("size") or 0),
        "output_suffix": str(raw.get("output_suffix") or "_Patched"),
        "files": normalized,
    }


def inspect_patch(patch_path: str) -> dict:
    if not patch_path or not os.path.isfile(patch_path):
        raise RuntimeError("ملف الباتش غير موجود.")
    try:
        with zipfile.ZipFile(patch_path, "r") as zf:
            names = zf.namelist()
            if "patch.json" not in names:
                raise RuntimeError("ملف الباتش لا يحتوي patch.json.")
            for name in names:
                if not _safe_member(name):
                    raise RuntimeError("مسار غير آمن داخل الباتش: " + name)
            try:
                raw = json.loads(zf.read("patch.json").decode("utf-8-sig"))
            except Exception as e:
                raise RuntimeError("تعذر قراءة patch.json: " + str(e))
            manifest = _load_manifest_dict(raw)
            romfs_names = {
                n[len("romfs/"):]: n
                for n in names
                if n.startswith("romfs/") and not n.endswith("/")
            }
            missing = sorted(set(manifest["files"]) - set(romfs_names))
            extra = sorted(set(romfs_names) - set(manifest["files"]))
            if missing:
                raise RuntimeError("ملفات مفقودة داخل الباتش: " + ", ".join(missing[:8]))
            if extra:
                raise RuntimeError("ملفات غير مسجلة في manifest: " + ", ".join(extra[:8]))
            for rel, expected in manifest["files"].items():
                actual = _sha256_bytes(zf.read(romfs_names[rel]))
                if actual != expected:
                    raise RuntimeError("فشل SHA-256 لملف الباتش: " + rel)
            manifest["patch_path"] = os.path.abspath(patch_path)
            manifest["patch_sha256"] = _sha256_file(patch_path)
            manifest["file_count"] = len(manifest["files"])
            return manifest
    except zipfile.BadZipFile:
        raise RuntimeError("ملف الباتش ليس حزمة AH3P/ZIP صالحة.")


def validate_source(game_path: str, manifest: dict):
    if not game_path or not os.path.isfile(game_path):
        return False, "ملف اللعبة غير موجود."
    if Path(game_path).suffix.lower() not in (".3ds", ".cci"):
        return False, "اختر ملف لعبة بصيغة .3ds أو .cci."
    try:
        size = os.path.getsize(game_path)
        if manifest.get("source_size") and size != manifest["source_size"]:
            return False, "حجم ملف اللعبة لا يطابق النسخة المطلوبة لهذا الباتش."
        with open(game_path, "rb") as f:
            f.seek(0x100)
            if f.read(4) != b"NCSD":
                return False, "الملف المحدد ليس صورة Nintendo 3DS صالحة (NCSD)."
        digest = _sha256_file(game_path)
    except OSError as e:
        return False, "تعذر قراءة ملف اللعبة: " + str(e)
    if digest.lower() not in manifest["source_sha256"]:
        return False, (
            "نسخة اللعبة غير مطابقة لهذا الباتش.\n\n"
            "SHA-256 الحالي:\n" + digest + "\n\n"
            "القيم المقبولة:\n" + "\n".join(manifest["source_sha256"])
        )
    return True, digest


def _extract_patch(patch_path: str, dest: str, manifest: dict) -> str:
    root = Path(dest).resolve()
    with zipfile.ZipFile(patch_path, "r") as zf:
        for info in zf.infolist():
            if not _safe_member(info.filename):
                raise RuntimeError("مسار غير آمن داخل الباتش: " + info.filename)
            out = (root / info.filename).resolve()
            if root != out and root not in out.parents:
                raise RuntimeError("مسار غير مسموح داخل الباتش.")
        zf.extractall(root)
    romfs = root / "romfs"
    if not romfs.is_dir():
        raise RuntimeError("الباتش لا يحتوي مجلد romfs.")
    for rel, expected in manifest["files"].items():
        p = romfs / Path(rel)
        if not p.is_file() or _sha256_file(str(p)) != expected:
            raise RuntimeError("فشل التحقق من ملف الباتش بعد الفك: " + rel)
    return str(romfs)


def _copy_with_progress(src: str, dst: str, start: int, end: int) -> None:
    size = os.path.getsize(src)
    done = 0
    with open(src, "rb") as fi, open(dst, "wb") as fo:
        while True:
            block = fi.read(8 * 1024 * 1024)
            if not block:
                break
            fo.write(block)
            done += len(block)
            if size:
                _report("نسخ ملف اللعبة إلى مساحة العمل", start + (end - start) * done / size)
    shutil.copystat(src, dst)


def _run(cmd, cwd: str, log_path: str, label: str, pct: int) -> None:
    _report(label, pct)
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    proc = subprocess.run(
        [str(x) for x in cmd], cwd=cwd,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", creationflags=flags,
    )
    with open(log_path, "a", encoding="utf-8", errors="replace") as log:
        log.write("\n>>> " + subprocess.list2cmdline([str(x) for x in cmd]) + "\n")
        log.write(proc.stdout or "")
        log.write("\n[exit=%d]\n" % proc.returncode)
    if proc.returncode != 0:
        raise RuntimeError(label + " فشل.\n\n" + (proc.stdout or "")[-1800:])


def _ncsd_partitions(path: str) -> list[int]:
    # NCSD partition table: 8 entries at 0x120, each offset+size in media units.
    with open(path, "rb") as f:
        f.seek(0x120)
        table = f.read(8 * 8)
    if len(table) != 64:
        raise RuntimeError("تعذر قراءة جدول أقسام NCSD.")
    parts = []
    for i in range(8):
        off = int.from_bytes(table[i * 8:i * 8 + 4], "little")
        size = int.from_bytes(table[i * 8 + 4:i * 8 + 8], "little")
        if off and size:
            parts.append(i)
    if 0 not in parts:
        raise RuntimeError("Partition 0 غير موجود في ملف اللعبة.")
    return parts


def _overlay_tree(src: str, dst: str, file_count: int, start=42, end=55) -> None:
    src_root = Path(src)
    dst_root = Path(dst)
    files = sorted((p for p in src_root.rglob("*") if p.is_file()), key=lambda p: str(p).lower())
    if len(files) != file_count:
        raise RuntimeError("عدد ملفات الباتش تغير أثناء العملية.")
    for i, p in enumerate(files, 1):
        rel = p.relative_to(src_root)
        out = dst_root / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, out)
        _report("دمج: " + rel.as_posix(), start + (end - start) * i / max(1, len(files)))


def _nonempty(path: str) -> bool:
    return os.path.isfile(path) and os.path.getsize(path) > 0


def _choose_output(source: str, suffix: str) -> str:
    p = Path(source)
    suffix = suffix or "_Patched"
    base = p.with_name(p.stem + suffix + ".3ds")
    if not base.exists():
        return str(base)
    for n in range(2, 1000):
        cand = p.with_name(p.stem + suffix + f"_{n}.3ds")
        if not cand.exists():
            return str(cand)
    raise RuntimeError("تعذر اختيار اسم ملف ناتج جديد.")


def _verify_patched_tree(verify_root: str, manifest: dict) -> None:
    root = Path(verify_root)
    total = len(manifest["files"])
    for i, (rel, expected) in enumerate(sorted(manifest["files"].items()), 1):
        p = root / Path(rel)
        if not p.is_file():
            raise RuntimeError("ملف التعريب مفقود من ROM الناتج: " + rel)
        actual = _sha256_file(str(p))
        if actual != expected:
            raise RuntimeError("ملف التعريب داخل ROM الناتج لا يطابق الباتش: " + rel)
        _report("التحقق من الملف الناتج: " + rel, 86 + 7 * i / max(1, total))


def apply_patch(patch_path: str, game_path: str):
    global LAST_OUTPUT, LAST_OUTPUT_SHA256, LAST_PATCH
    LAST_OUTPUT = None
    LAST_OUTPUT_SHA256 = None
    LAST_PATCH = None

    if os.name != "nt":
        raise RuntimeError("هذه النسخة من الأداة مخصصة لنظام Windows.")

    manifest = inspect_patch(patch_path)
    LAST_PATCH = manifest
    source = os.path.abspath(game_path or "")
    ok, detail = validate_source(source, manifest)
    if not ok:
        raise RuntimeError(detail)

    final_output = _choose_output(source, manifest["output_suffix"])
    free = shutil.disk_usage(tempfile.gettempdir()).free
    required = max(3_500_000_000, os.path.getsize(source) * 3)
    if free < required:
        raise RuntimeError("المساحة الحرة غير كافية في قرص ملفات Windows المؤقتة.")

    work = tempfile.mkdtemp(prefix="AH3DPatcher_")
    log_path = os.path.join(work, "patcher.log")
    error_log = os.path.join(os.path.dirname(source), "Arabic_Hesham_3DS_Patcher_Error.log")
    partial_output = os.path.join(work, "patched_output.3ds")
    source_hash = detail

    try:
        tool = resource_path(os.path.join("tools", "3dstool.exe"))
        if not os.path.isfile(tool):
            raise RuntimeError("الأداة تالفة: tools\\3dstool.exe غير موجود.")

        _report("فك الباتش والتحقق منه", 2)
        patch_root = _extract_patch(patch_path, os.path.join(work, "patch"), manifest)

        local_source = os.path.join(work, "source.3ds")
        _copy_with_progress(source, local_source, 5, 14)
        parts = _ncsd_partitions(local_source)

        ncsd_header = os.path.join(work, "ncsd_header.bin")
        part_files = {i: os.path.join(work, f"partition{i}.bin") for i in parts}
        cmd = [tool, "-xtf", "3ds", local_source, "--header", ncsd_header]
        for i in parts:
            cmd += [f"-{i}", part_files[i]]
        _run(cmd, work, log_path, "استخراج أقسام اللعبة", 18)

        p0 = part_files[0]
        ncch_header = os.path.join(work, "ncch0_header.bin")
        exheader = os.path.join(work, "exheader.bin")
        exefs = os.path.join(work, "exefs.bin")
        romfs_bin = os.path.join(work, "romfs.bin")
        logo = os.path.join(work, "logo.bin")
        plain = os.path.join(work, "plain.bin")
        _run([tool, "-xtf", "cxi", p0,
              "--header", ncch_header, "--exh", exheader,
              "--exefs", exefs, "--romfs", romfs_bin,
              "--logo", logo, "--plain", plain],
             work, log_path, "استخراج RomFS الأصلي", 25)

        romfs_dir = os.path.join(work, "romfs_original")
        os.makedirs(romfs_dir, exist_ok=True)
        _run([tool, "-xtf", "romfs", romfs_bin, "--romfs-dir", romfs_dir],
             work, log_path, "فك ملفات RomFS", 33)

        _overlay_tree(patch_root, romfs_dir, manifest["file_count"])

        custom_romfs = os.path.join(work, "romfs_patched.bin")
        _run([tool, "-ctf", "romfs", custom_romfs, "--romfs-dir", romfs_dir],
             work, log_path, "إعادة بناء RomFS", 60)

        new_p0 = os.path.join(work, "partition0_patched.cxi")
        cxi_cmd = [tool, "-ctf", "cxi", new_p0,
                   "--header", ncch_header, "--exh", exheader,
                   "--exefs", exefs, "--romfs", custom_romfs]
        if _nonempty(logo):
            cxi_cmd += ["--logo", logo]
        if _nonempty(plain):
            cxi_cmd += ["--plain", plain]
        _run(cxi_cmd, work, log_path, "إعادة بناء Partition 0", 69)

        out_cmd = [tool, "-ctf", "3ds", partial_output, "--header", ncsd_header]
        for i in parts:
            out_cmd += [f"-{i}", new_p0 if i == 0 else part_files[i]]
        _run(out_cmd, work, log_path, "إنشاء نسخة اللعبة المعدلة", 77)

        with open(partial_output, "rb") as f:
            f.seek(0x100)
            if f.read(4) != b"NCSD":
                raise RuntimeError("الملف الناتج لا يحتوي ترويسة NCSD صحيحة.")

        verify_header = os.path.join(work, "verify_ncsd.bin")
        verify_p0 = os.path.join(work, "verify_p0.cxi")
        verify_ncch = os.path.join(work, "verify_ncch.bin")
        verify_romfs = os.path.join(work, "verify_romfs.bin")
        verify_dir = os.path.join(work, "verify_romfs")
        _run([tool, "-xtf", "3ds", partial_output, "--header", verify_header, "-0", verify_p0],
             work, log_path, "التحقق من ملف اللعبة الناتج", 82)
        _run([tool, "-xtf", "cxi", verify_p0, "--header", verify_ncch, "--romfs", verify_romfs],
             work, log_path, "استخراج RomFS للتحقق", 84)
        os.makedirs(verify_dir, exist_ok=True)
        _run([tool, "-xtf", "romfs", verify_romfs, "--romfs-dir", verify_dir],
             work, log_path, "فك RomFS للتحقق", 85)
        _verify_patched_tree(verify_dir, manifest)

        _report("التأكد من بقاء الملف الأصلي دون تعديل", 94)
        if _sha256_file(source) != source_hash:
            raise RuntimeError("تغير الملف الأصلي أثناء العملية؛ تم إيقاف الحفظ لحمايته.")

        shutil.move(partial_output, final_output)
        LAST_OUTPUT = final_output
        LAST_OUTPUT_SHA256 = _sha256_file(
            final_output,
            lambda d, t: _report("حساب SHA-256 للناتج", 95 + 4 * d / t),
        )
        _report("اكتمل الدمج", 100)
        try:
            if os.path.exists(error_log):
                os.remove(error_log)
        except OSError:
            pass
        return "ok"

    except Exception:
        try:
            if os.path.isfile(log_path):
                shutil.copy2(log_path, error_log)
        except OSError:
            pass
        try:
            if os.path.isfile(partial_output):
                os.remove(partial_output)
        except OSError:
            pass
        raise
    finally:
        shutil.rmtree(work, ignore_errors=True)
