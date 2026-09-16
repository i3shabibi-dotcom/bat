# -*- coding: utf-8 -*-
"""Story of Seasons: Trio of Towns Arabic installer engine.

The installer never modifies the selected source ROM. It validates the exact
known USA source, rebuilds only partition 0 with the bundled RomFS overlay,
and carries original partitions 1/6/7 through unchanged.

For Azahar, the same verified RomFS overlay is also installed into LayeredFS
when a standard Azahar user directory is detected. This prevents an installed
update layer from hiding localized files in the rebuilt base image.
"""
import hashlib
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

import loc_crypto

GAME_NAME = "STORY OF SEASONS: Trio of Towns"
TITLE_ID = "000400000019F500"
UPDATE_TITLE_ID = "0004000E0019F500"
SOURCE_SIZE = 1_073_741_824
SOURCE_SHA256 = "146cb1cc2d8c63cad81ced4e0a18b13672488dd52fd810501437e64934a1aab1"
PROGRESS_CB = None
LAST_OUTPUT = None
LAST_OUTPUT_SHA256 = None
LAST_AZAHAR_MOD_PATH = None


def _key() -> bytes:
    parts = [b"trio", b"of", b"towns", b"arabic", b"hesham"]
    return hashlib.sha256(b"|".join(parts) + b"|USA-v1.1-ROMFS-2026").digest()


def resource_path(rel: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


def _report(name: str, pct: int) -> None:
    if PROGRESS_CB:
        PROGRESS_CB(name, max(0, min(100, int(pct))))


def _append_log(log_path: str, text: str) -> None:
    try:
        with open(log_path, "a", encoding="utf-8", errors="replace") as log:
            log.write(text.rstrip() + "\n")
    except OSError:
        pass


def _sha256(path: str, cb=None) -> str:
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


def validate_source(path: str):
    if not path or not os.path.isfile(path):
        return False, "ملف اللعبة غير موجود."
    if Path(path).suffix.lower() not in (".3ds", ".cci"):
        return False, "اختر ملف اللعبة الأصلي بصيغة .3ds أو .cci."
    try:
        if os.path.getsize(path) != SOURCE_SIZE:
            return False, "حجم الملف لا يطابق النسخة الأمريكية المعتمدة."
        with open(path, "rb") as f:
            f.seek(0x100)
            if f.read(4) != b"NCSD":
                return False, "الملف المحدد ليس صورة Nintendo 3DS صالحة (NCSD)."
        digest = _sha256(path)
    except OSError as e:
        return False, "تعذر قراءة ملف اللعبة: " + str(e)
    if digest.lower() != SOURCE_SHA256:
        return False, (
            "نسخة اللعبة غير مطابقة للإصدار المطلوب.\n\n"
            "SHA-256 الحالي:\n" + digest + "\n\n"
            "SHA-256 المطلوب:\n" + SOURCE_SHA256
        )
    return True, digest


def find_game():
    return None


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
                pct = start + (end - start) * done / size
                _report("نسخ ملف اللعبة إلى مساحة العمل", pct)
    shutil.copystat(src, dst)


def _safe_extract_zip(data: bytes, dest: str) -> None:
    root = Path(dest).resolve()
    with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
        for info in zf.infolist():
            name = info.filename.replace("\\", "/")
            p = Path(name)
            if p.is_absolute() or ".." in p.parts:
                raise RuntimeError("حزمة التعريب تحتوي مساراً غير آمن: " + info.filename)
            out = (root / p).resolve()
            if root != out and root not in out.parents:
                raise RuntimeError("حزمة التعريب تحتوي مساراً خارجياً غير مسموح.")
        zf.extractall(root)


def _payload_root(extracted: str) -> str:
    root = Path(extracted)
    entries = [p for p in root.iterdir() if p.name not in ("__MACOSX",)]
    if len(entries) == 1 and entries[0].is_dir() and entries[0].name.lower() == "romfs":
        return str(entries[0])
    return str(root)


def _payload_files(root: str):
    r = Path(root)
    return sorted(
        (p for p in r.rglob("*") if p.is_file()),
        key=lambda p: p.relative_to(r).as_posix().lower(),
    )


def _validate_payload(root: str) -> None:
    r = Path(root)
    required = [
        r / "Msg.xbb",
        r / "DataText.xbb",
        r / "Font" / "mainfont.bffnt",
        r / "Font" / "subfont.bffnt",
        r / "Layout" / "ListSelect.arc",
    ]
    missing = [str(p.relative_to(r)) for p in required if not p.is_file()]
    if missing:
        raise RuntimeError("حزمة RomFS ناقصة. الملفات المفقودة:\n" + "\n".join(missing))


def _overlay_tree(src: str, dst: str, start_pct=43, end_pct=56) -> int:
    src_root = Path(src)
    dst_root = Path(dst)
    files = _payload_files(src)
    total = max(1, len(files))
    for i, p in enumerate(files, 1):
        rel = p.relative_to(src_root)
        out = dst_root / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, out)
        pct = start_pct + (end_pct - start_pct) * i / total
        _report("دمج ملفات التعريب: " + rel.as_posix(), pct)
    return len(files)


def _verify_overlay_files(payload_root: str, romfs_root: str, log_path: str) -> int:
    src_root = Path(payload_root)
    dst_root = Path(romfs_root)
    files = _payload_files(payload_root)
    failures = []
    for p in files:
        rel = p.relative_to(src_root)
        out = dst_root / rel
        if not out.is_file():
            failures.append(rel.as_posix() + " [MISSING]")
            continue
        src_hash = _sha256(str(p))
        dst_hash = _sha256(str(out))
        if src_hash != dst_hash:
            failures.append(rel.as_posix() + " [HASH MISMATCH]")
    _append_log(log_path, f"Per-file RomFS verification: {len(files) - len(failures)}/{len(files)} matched")
    if failures:
        for item in failures:
            _append_log(log_path, "VERIFY_FAIL " + item)
        raise RuntimeError(
            "فشل التحقق من ملفات التعريب داخل ROM الناتج.\n\n" +
            "\n".join(failures[:20])
        )
    return len(files)


def _run(cmd, cwd: str, log_path: str, label: str, pct: int) -> None:
    _report(label, pct)
    flags = 0
    if os.name == "nt":
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    proc = subprocess.run(
        [str(x) for x in cmd],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=flags,
    )
    with open(log_path, "a", encoding="utf-8", errors="replace") as log:
        log.write("\n>>> " + subprocess.list2cmdline([str(x) for x in cmd]) + "\n")
        log.write(proc.stdout or "")
        log.write("\n[exit=%d]\n" % proc.returncode)
    if proc.returncode != 0:
        tail = (proc.stdout or "")[-1800:]
        raise RuntimeError(label + " فشل.\n\n" + tail)


def _nonempty(path: str) -> bool:
    return os.path.isfile(path) and os.path.getsize(path) > 0


def _choose_output(source: str) -> str:
    p = Path(source)
    base = p.with_name(p.stem + "_Arabic_Hesham.3ds")
    if not base.exists():
        return str(base)
    for n in range(2, 1000):
        cand = p.with_name(p.stem + f"_Arabic_Hesham_{n}.3ds")
        if not cand.exists():
            return str(cand)
    raise RuntimeError("تعذر اختيار اسم ملف ناتج جديد.")


def _check_ncsd(path: str) -> None:
    if not os.path.isfile(path) or os.path.getsize(path) < 0x200:
        raise RuntimeError("لم يتم إنشاء ملف 3DS الناتج بصورة صحيحة.")
    with open(path, "rb") as f:
        f.seek(0x100)
        if f.read(4) != b"NCSD":
            raise RuntimeError("ملف 3DS الناتج لا يحتوي ترويسة NCSD صحيحة.")


def _azahar_user_candidates():
    candidates = []
    explicit = os.environ.get("AZAHAR_USER_DIR")
    if explicit:
        candidates.append(Path(explicit))
    appdata = os.environ.get("APPDATA")
    if appdata:
        candidates.append(Path(appdata) / "Azahar")
        candidates.append(Path(appdata) / "azahar-emu")
    local = os.environ.get("LOCALAPPDATA")
    if local:
        candidates.append(Path(local) / "Azahar")
        candidates.append(Path(local) / "azahar-emu")
    unique = []
    seen = set()
    for p in candidates:
        key = str(p).lower()
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique


def _has_azahar_markers(path: Path) -> bool:
    if not path.is_dir():
        return False
    markers = ["nand", "sdmc", "load", "config"]
    return any((path / name).exists() for name in markers)


def _detect_separate_update(user_dir: Path) -> bool:
    nand = user_dir / "nand"
    if not nand.is_dir():
        return False
    update_high = UPDATE_TITLE_ID[:8].lower()
    update_low = UPDATE_TITLE_ID[8:].lower()
    try:
        for high in nand.rglob(update_high):
            if high.is_dir() and (high / update_low).is_dir():
                return True
    except OSError:
        return False
    return False


def _install_azahar_layeredfs(payload_root: str, log_path: str):
    """Install verified overlay into detected Azahar user folders.

    Returns the first installed mod path or None. Failure here never destroys
    the rebuilt ROM; errors are logged and the standalone ROM remains valid.
    """
    src_root = Path(payload_root)
    installed = []
    for user_dir in _azahar_user_candidates():
        if not _has_azahar_markers(user_dir):
            continue
        mod_romfs = user_dir / "load" / "mods" / TITLE_ID / "romfs"
        try:
            mod_romfs.mkdir(parents=True, exist_ok=True)
            for src in _payload_files(payload_root):
                rel = src.relative_to(src_root)
                dst = mod_romfs / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                if _sha256(str(src)) != _sha256(str(dst)):
                    raise RuntimeError("Azahar LayeredFS hash mismatch: " + rel.as_posix())
            installed.append(str(mod_romfs))
            update_state = "YES" if _detect_separate_update(user_dir) else "NO/NOT-DETECTED"
            _append_log(log_path, "Azahar LayeredFS installed: " + str(mod_romfs))
            _append_log(log_path, "Azahar separate update detected: " + update_state)
        except Exception as exc:
            _append_log(log_path, "Azahar LayeredFS warning: " + repr(exc))
    return installed[0] if installed else None


def main(game_path=None):
    global LAST_OUTPUT, LAST_OUTPUT_SHA256, LAST_AZAHAR_MOD_PATH
    LAST_OUTPUT = None
    LAST_OUTPUT_SHA256 = None
    LAST_AZAHAR_MOD_PATH = None

    if os.name != "nt":
        raise RuntimeError("هذا المثبت مخصص لنظام Windows.")
    source = os.path.abspath(game_path or "")
    ok, detail = validate_source(source)
    if not ok:
        raise RuntimeError(detail)

    final_output = _choose_output(source)
    temp_parent = tempfile.gettempdir()
    free = shutil.disk_usage(temp_parent).free
    if free < 3_500_000_000:
        raise RuntimeError("المساحة الحرة غير كافية. يلزم توفر 3.5 GB على الأقل في قرص ملفات Windows المؤقتة.")

    work = tempfile.mkdtemp(prefix="TrioArabic_")
    log_path = os.path.join(work, "patcher.log")
    partial_output = os.path.join(work, "ArabicOutput.3ds")
    error_log = os.path.join(os.path.dirname(source), "Trio_Arabic_Patcher_Error.log")

    try:
        tool = resource_path(os.path.join("tools", "3dstool.exe"))
        enc = resource_path(os.path.join("data", "patch.enc"))
        if not os.path.isfile(tool):
            raise RuntimeError("المثبت تالف: tools\\3dstool.exe غير موجود.")
        if not os.path.isfile(enc):
            raise RuntimeError("المثبت تالف: data\\patch.enc غير موجود.")

        local_source = os.path.join(work, "source.3ds")
        _report("بدء العملية", 2)
        _copy_with_progress(source, local_source, 4, 14)

        _report("فك حزمة التعريب الداخلية", 16)
        with open(enc, "rb") as f:
            payload_zip = loc_crypto.decrypt(f.read(), _key())
        patch_extract = os.path.join(work, "patch")
        os.makedirs(patch_extract, exist_ok=True)
        _safe_extract_zip(payload_zip, patch_extract)
        patch_root = _payload_root(patch_extract)
        _validate_payload(patch_root)
        _append_log(log_path, "Payload file count: %d" % len(_payload_files(patch_root)))

        ncsd_header = os.path.join(work, "ncsd_header.bin")
        p0 = os.path.join(work, "partition0.cxi")
        p1 = os.path.join(work, "partition1.cfa")
        p6 = os.path.join(work, "partition6.cfa")
        p7 = os.path.join(work, "partition7.cfa")

        _run([tool, "-xtf", "3ds", local_source,
              "--header", ncsd_header,
              "-0", p0, "-1", p1, "-6", p6, "-7", p7],
             work, log_path, "استخراج أقسام اللعبة", 20)

        ncch0_header = os.path.join(work, "ncch0_header.bin")
        exheader = os.path.join(work, "exheader.bin")
        exefs = os.path.join(work, "exefs.bin")
        romfs_bin = os.path.join(work, "romfs.bin")
        logo = os.path.join(work, "logo.bin")
        plain = os.path.join(work, "plain.bin")

        _run([tool, "-xtf", "cxi", p0,
              "--header", ncch0_header,
              "--exh", exheader,
              "--exefs", exefs,
              "--romfs", romfs_bin,
              "--logo", logo,
              "--plain", plain],
             work, log_path, "استخراج RomFS الأصلي", 27)

        romfs_dir = os.path.join(work, "romfs_original")
        os.makedirs(romfs_dir, exist_ok=True)
        _run([tool, "-xtf", "romfs", romfs_bin, "--romfs-dir", romfs_dir],
             work, log_path, "فك ملفات RomFS", 35)

        count = _overlay_tree(patch_root, romfs_dir, 43, 56)
        if count == 0:
            raise RuntimeError("حزمة التعريب فارغة.")

        custom_romfs = os.path.join(work, "romfs_arabic.bin")
        _run([tool, "-ctf", "romfs", custom_romfs, "--romfs-dir", romfs_dir],
             work, log_path, "إعادة بناء RomFS العربي", 61)

        new_p0 = os.path.join(work, "partition0_arabic.cxi")
        cxi_cmd = [tool, "-ctf", "cxi", new_p0,
                   "--header", ncch0_header,
                   "--exh", exheader,
                   "--exefs", exefs,
                   "--romfs", custom_romfs]
        if _nonempty(logo):
            cxi_cmd += ["--logo", logo]
        if _nonempty(plain):
            cxi_cmd += ["--plain", plain]
        _run(cxi_cmd, work, log_path, "إعادة بناء القسم الرئيسي", 70)

        cci_cmd = [tool, "-ctf", "3ds", partial_output,
                   "--header", ncsd_header, "-0", new_p0]
        for flag, part in (("-1", p1), ("-6", p6), ("-7", p7)):
            if _nonempty(part):
                cci_cmd += [flag, part]
        _run(cci_cmd, work, log_path, "إنشاء نسخة اللعبة العربية", 79)
        _check_ncsd(partial_output)

        verify_header = os.path.join(work, "verify_ncsd.bin")
        verify_p0 = os.path.join(work, "verify_p0.cxi")
        verify_ncch = os.path.join(work, "verify_ncch.bin")
        verify_romfs = os.path.join(work, "verify_romfs.bin")
        _run([tool, "-xtf", "3ds", partial_output,
              "--header", verify_header, "-0", verify_p0],
             work, log_path, "التحقق من ملف اللعبة الناتج", 84)
        _run([tool, "-xtf", "cxi", verify_p0,
              "--header", verify_ncch, "--romfs", verify_romfs],
             work, log_path, "التحقق من RomFS الناتج", 88)
        if _sha256(custom_romfs) != _sha256(verify_romfs):
            raise RuntimeError("فشل التحقق النهائي: RomFS داخل الملف الناتج لا يطابق RomFS المبني.")

        verify_romfs_dir = os.path.join(work, "verify_romfs_dir")
        os.makedirs(verify_romfs_dir, exist_ok=True)
        _run([tool, "-xtf", "romfs", verify_romfs, "--romfs-dir", verify_romfs_dir],
             work, log_path, "التحقق من كل ملفات التعريب", 89)
        verified_count = _verify_overlay_files(patch_root, verify_romfs_dir, log_path)
        _append_log(log_path, "Verified localized files in final ROM: %d" % verified_count)

        _report("التأكد من بقاء الملف الأصلي دون تعديل", 91)
        if _sha256(source) != SOURCE_SHA256:
            raise RuntimeError("تغير الملف الأصلي أثناء العملية؛ تم إيقاف التثبيت لحمايته.")

        _report("حفظ النسخة العربية", 94)
        shutil.move(partial_output, final_output)
        LAST_OUTPUT = final_output
        LAST_OUTPUT_SHA256 = _sha256(
            final_output,
            lambda d, t: _report("حساب SHA-256 للناتج", 95 + 3 * d / t),
        )

        _report("تطبيق توافق Azahar", 99)
        LAST_AZAHAR_MOD_PATH = _install_azahar_layeredfs(patch_root, log_path)
        _report("اكتمل", 100)

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
