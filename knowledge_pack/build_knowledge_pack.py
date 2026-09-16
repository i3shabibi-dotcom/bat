from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "dist" / "3DS_ARABIC_LOCALIZATION_KNOWLEDGE_PACK"


def clean():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)


def write(rel: str, text: str):
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(text).lstrip("\n").rstrip() + "\n", encoding="utf-8")


def write_json(rel: str, obj):
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(rel: str, rows):
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerows(rows)


def copy_if_exists(src: Path, rel: str):
    if src.exists():
        dst = OUT / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


COMMON_TASK_FORMAT = """
Every delegated task must use this exact envelope:

TARGET ROLE:
[SUPERVISOR | TRANSLATOR / LOCALIZATION ENGINEER | BUILDER / INTEGRATION ENGINEER | RUNTIME QA TESTER | SPECIALIST]

OBJECTIVE:
[one precise objective]

INPUT FILES:
[exact paths or exact file categories]

ATTACHMENTS REQUIRED:
YES / NO

ATTACHMENTS:
[exact files; use one ZIP when several related files belong together]

KNOWN CONTEXT:
[only facts the receiver needs; mark VERIFIED / LIKELY / UNKNOWN]

DO NOT CHANGE:
[protected known-good components]

TASK:
[detailed technical instruction]

SUCCESS CRITERIA:
[objective, testable criteria]

RETURN TO SUPERVISOR:
[exact artifacts, hashes, screenshots, logs, diffs, reports]

NEXT ROUTE IF SUCCESSFUL:
[next role]

NEXT ROUTE IF FAILED:
[role that diagnoses the failure]
"""


def build_docs():
    write("README.md", r"""
    # 3DS Arabic Localization Team Knowledge Pack

    This pack transfers reusable engineering practice from a completed Nintendo 3DS Arabic localization project. It is intentionally organized as operational knowledge, not project history.

    ## Use order
    1. Read `00_START_HERE/QUICK_START.md`.
    2. Give `15_PROMPT_LIBRARY/01_NEW_SUPERVISOR_MASTER_PROMPT.txt` to the new Supervisor.
    3. Copy `NEW_3DS_ARABIC_PROJECT/` for the new game.
    4. Run only the short discovery protocol needed to identify differences from the known pipeline.
    5. Prove round-trip rebuild, control-code safety, Arabic font/rendering, and one end-to-end string before scaling translation.

    ## Evidence labels
    - **VERIFIED**: proved by hashes, structural checks, build output, or runtime evidence.
    - **LIKELY**: evidence supports the conclusion, but runtime or exact binary proof is incomplete.
    - **UNKNOWN**: do not guess. Create a focused discovery task.

    ## Reusability labels
    - **REUSABLE**: can be reused as-is or with project configuration.
    - **PARTIALLY REUSABLE**: method is reusable, binary details must be revalidated.
    - **GAME-SPECIFIC — REVALIDATE**: retain only as a reference; do not transplant assumptions.

    No ROM, CIA, copyrighted game archive, donor font binary, or localized RomFS payload is included.
    """)

    write("00_START_HERE/QUICK_START.md", r"""
    # Quick Start

    ## First 12 actions
    1. Create a read-only `original/` source area and a separate writable workspace.
    2. Record title, region, version/update state, product code, Title ID / Program ID, container type, size, and SHA-256.
    3. Inventory NCSD/NCCH partitions, ExeFS, RomFS, fonts, likely text archives, and layout/texture resources.
    4. Compare discoveries against `10_VALIDATION/REUSABILITY_MATRIX.md`.
    5. Do not translate at scale yet.
    6. Prove text extraction -> no-op reinsertion -> rebuild. Prefer byte-identical; otherwise require structural + semantic equality with an explained binary delta.
    7. Inventory control codes/placeholders from the actual target game and enable per-record validation before translation.
    8. Determine font format and whether Arabic glyph coverage is native. Run a small BFFNT/font PoC if needed.
    9. Run Arabic shaping/RTL PoC using natural-order Arabic source text; keep transformation in the build stage.
    10. Test one dialogue, one menu label, one mixed-direction string, one number/punctuation case, and one narrow UI string in Runtime.
    11. Lock known-good pipeline components and hashes.
    12. Scale translation only after extraction, reinsertion, control-code safety, Arabic rendering, and Runtime PoC pass.

    ## Non-negotiable engineering rules
    - Never modify the only source copy.
    - Never claim Runtime success from static inspection.
    - Do not edit `code.bin` until RomFS-only limitations are demonstrated by evidence.
    - Do not translate engine identifiers merely because they are printable ASCII.
    - Do not reopen a frozen working subsystem without new evidence implicating it.
    - Backend/tool failure is not project failure. Move execution to a viable environment and preserve the method.
    """)

    write("00_START_HERE/DELIVERABLE_INDEX.md", r"""
    # Deliverable Index
    - Supervisor management system: `01_SUPERVISOR/`
    - Translation rules/templates: `02_TRANSLATOR/`
    - Builder technical playbook: `03_BUILDER/`
    - Runtime QA system: `04_RUNTIME_QA/`
    - Discovery/extraction: `05_EXTRACTION/`
    - Text pipeline: `06_TEXT_PIPELINE/`
    - Arabic font: `07_ARABIC_FONT/`
    - RTL/rendering: `08_RTL_AND_RENDERING/`
    - Build/reinsertion/patching: `09_BUILD_AND_REINSERTION/`
    - Validation/baselines: `10_VALIDATION/`
    - Testing: `11_TESTING/`
    - Reusable scripts: `12_SCRIPTS/`
    - Legal-safe references and final-source snapshots: `13_REFERENCE_FILES/`
    - Failure-prevention rules: `14_FAILURE_CASES/`
    - Ready-to-paste prompts: `15_PROMPT_LIBRARY/`
    - Bootstrap and attachment routing: `16_PROJECT_BOOTSTRAP/`
    - Local-computer fallback template: `17_LOCAL_EXECUTION/`
    - Copyable new-project tree: `NEW_3DS_ARABIC_PROJECT/`
    """)

    supervisor = r"""
    # Supervisor Operating Model

    ## Mission
    Maintain a single evidence-based project state, route work to the correct role, protect known-good components, and force every technical conclusion to be reproducible.

    ## Routing
    - Linguistic meaning, terminology, visible wording, consistency, context, register -> Translator / Localization Engineer.
    - Binary extraction/reinsertion, archive formats, fonts, textures, shaping/RTL implementation, build, patching, validation tooling -> Builder / Integration Engineer.
    - In-game verification, screenshots, clipping, overflow, color, missing glyphs, broken joining, untranslated visible text, crashes/freezes, regressions -> Runtime QA Tester.
    - Sequencing, baseline control, evidence arbitration, scope/freeze decisions, ownership, handoffs -> Supervisor.
    - Add a specialist only when a narrow unknown is not efficiently owned by the four core roles (for example, reverse-engineering a proprietary compression or renderer routine).

    ## Supervisor state must always contain
    - CURRENT STATE
    - CURRENT BASELINE
    - CURRENT BUILD
    - OPEN DEFECTS
    - FROZEN / DO NOT CHANGE
    - CURRENT OWNER
    - NEXT ACTION
    - NEXT ROLE
    - BLOCKERS
    - VERIFIED / LIKELY / UNKNOWN facts

    ## Evidence discipline
    A fix is not accepted because an agent says "it should work". Accept only the evidence appropriate to the layer:
    - archive/text tooling: round-trip + structure + token validation;
    - font/rendering: binary validation + Runtime screenshots;
    - build: hashes + successful rebuild + output re-extraction comparison;
    - Runtime defect: screenshot/log + reproduction steps + build ID;
    - release: clean source -> reproducible build -> output verification -> Runtime smoke/regression pass.

    ## Freeze discipline
    Once a subsystem is proven and frozen, a new task must state why that subsystem is implicated before modifying it. Prefer targeted fixes. If 95% works and one defect remains, do not rebuild architecture without evidence.
    """
    write("01_SUPERVISOR/SUPERVISOR_OPERATING_MODEL.md", supervisor)
    write("01_SUPERVISOR/TASK_ENVELOPE.md", COMMON_TASK_FORMAT)

    write("01_SUPERVISOR/ROLE_ROUTING_MATRIX.md", r"""
    # Role Routing Matrix

    | Task / Evidence | Primary owner | Required return |
    |---|---|---|
    | Translation meaning, terminology, naming, tone | Translator | updated translation records + change log |
    | Control tags/placeholders found in strings | Builder owns validator; Translator obeys policy | inventory + policy + validation report |
    | Text archive extraction/repack | Builder | scripts, no-op round-trip report, hashes |
    | BFFNT/font glyph support | Builder | font diff, mapping/metric report, Runtime handoff |
    | Arabic wording does not fit | Translator first if wording can change; Builder if layout/wrapping is the constraint | constrained wording or layout change, then QA |
    | Clipping/overflow in game | Runtime QA reports; Supervisor routes to Translator or Builder based on evidence | screenshot + scene + build ID |
    | Wrong color/style in UI | QA -> Builder | exact pane/resource evidence + targeted fix |
    | Visible untranslated English | QA -> Supervisor; Translator if translatable text, Builder if graphic/internal resource | screenshot + resource mapping |
    | Broken joins/reversed Arabic | QA -> Builder | minimal reproduction + affected string/resource |
    | Crash after reinsertion | Builder | build log + archive/structure checks + minimal corrupting delta |
    | Build/installer failure | Builder | exact stage, command log, hashes, environment |
    | Backend timeout / unavailable compiler | Supervisor routes same Builder task to Local Execution | local package + auto-collected failure bundle |
    | Release decision | Supervisor | completed release checklist and Runtime evidence |
    """)

    write("01_SUPERVISOR/PROJECT_STATE_TEMPLATE.md", r"""
    # PROJECT CONTROL
    CURRENT STATE:
    CURRENT BASELINE:
    CURRENT BUILD:
    OPEN DEFECTS:
    FROZEN / DO NOT CHANGE:
    CURRENT OWNER:
    NEXT ACTION:
    NEXT ROLE:
    BLOCKERS:

    VERIFIED:
    -
    LIKELY:
    -
    UNKNOWN:
    -
    """)

    write("01_SUPERVISOR/DO_NOT_BREAK_WORKING_COMPONENTS.md", r"""
    # DO NOT BREAK WORKING COMPONENTS

    Every engineering task that changes files must report:
    - FILES CHANGED
    - FILES NOT CHANGED
    - EXPECTED EFFECT
    - POSSIBLE REGRESSIONS
    - TESTS REQUIRED
    - BEFORE HASHES
    - AFTER HASHES

    Rules:
    1. Work from a named baseline, never an unlabeled "latest" folder.
    2. Keep originals immutable.
    3. Do not mix unrelated fixes in one build when a targeted build can isolate causality.
    4. Do not globally alter font metrics because one UI element is small; first prove the metric is globally wrong.
    5. Do not edit layout/animation files when a texture-only fix is sufficient; conversely, stop redrawing a tiny texture if Runtime proves the presentation box itself is the limiting factor.
    6. Do not change translated wording globally for a graphics/layout defect.
    7. Do not change code/ExeFS for a RomFS defect without evidence.
    """)

    write("01_SUPERVISOR/VERSIONING_POLICY.md", r"""
    # Versioning Policy
    Use deterministic component IDs:

    `<PROJECT>_<COMPONENT>_vNNN`

    Builds:
    `<PROJECT>_BUILD_vNNN_<short-purpose>`

    Patches:
    `<PROJECT>_<region>_<version>_<language>_vNNN.ah3p`

    Git:
    - one branch for active integration;
    - commits describe one technical change;
    - tag known-good gates: `gate-text-roundtrip`, `gate-token-safety`, `gate-arabic-poc`, `runtime-pass`, `release-candidate`;
    - never use `final2`, `new_final`, `real_final`.
    """)

    write("02_TRANSLATOR/TRANSLATION_RULES.md", r"""
    # Translator Rules

    ## Authoring rule
    Write Arabic in natural reading order. Do not manually reverse characters or pre-shape glyphs unless the Builder explicitly proves the new game requires stored visual-order text.

    ## Never alter blindly
    - control tags such as `<PAGE>`, `<POS_RIGHT>`, `<FACE_NORMAL>`;
    - dynamic placeholders such as player/item/character variables;
    - printf-like variables, numeric format fields, or engine escape sequences;
    - internal IDs, labels, filenames, resource keys, script commands.

    ## Placeholder policy
    Placeholders may be linguistically repositioned only when the Builder's validator classifies them as movable dynamic placeholders. Their spelling and required count must remain exact. Structural/control tags normally preserve sequence as well as count.

    ## Context
    Translate only records proven visible or intentionally localized. Keep speaker, scene, menu, item category, gender/number context, and length constraint in the translation worksheet.

    ## Length and UI
    Prefer clear Arabic over literal length matching. If a correct label does not fit, return a constraint issue rather than silently abbreviating critical meaning. The Supervisor decides whether wording or layout changes.

    ## Mixed content
    Preserve ASCII segments that are genuinely names, units, acronyms, button labels, or variables. Flag mixed Arabic/Latin/number strings for Runtime tests.

    ## Punctuation/numbers
    Do not apply global punctuation conversion without a rendering test. Record intended display, especially parentheses, slashes, colon, percent, plus/minus, currency, dates, and number ranges.
    """)

    write_csv("02_TRANSLATOR/GLOSSARY_TEMPLATE.csv", [
        ["source_term", "arabic_term", "category", "context", "gender_number", "do_not_translate", "approved_by", "notes"],
        ["", "", "UI/item/name/dialogue/system", "", "", "FALSE", "", ""],
    ])
    write_csv("02_TRANSLATOR/STRING_WORKSHEET_TEMPLATE.csv", [
        ["record_id", "archive", "label", "speaker", "context", "source", "arabic_natural_order", "tokens", "length_constraint", "mixed_direction", "status", "notes"],
        ["", "", "", "", "", "", "", "", "", "FALSE", "NEW", ""],
    ])

    write("03_BUILDER/BUILDER_PLAYBOOK.md", r"""
    # Builder / Integration Engineer Playbook

    ## Gate sequence
    1. Source identity and partition/resource inventory.
    2. Text-format no-op round-trip.
    3. Strict structural audit and control-token safety.
    4. Arabic font glyph PoC.
    5. Arabic shaping/RTL/BiDi PoC.
    6. One end-to-end translated record rebuilt into the game.
    7. Runtime smoke on dialogue/menu/mixed text/numbers.
    8. Lock pipeline, then scale translation.
    9. Continuous build + per-file verification + Runtime regression.

    ## Binary discipline
    - Hash important inputs and outputs with SHA-256.
    - Preserve unknown/reserved fields and alignments until their semantics are proved.
    - A semantically correct text dump is not enough: archive/PAPA/block/string-table structure must remain valid.
    - Re-extract rebuilt outputs and compare what the game will actually read.
    - Treat source-format anomalies as source-relative exceptions; do not "repair" them automatically unless Runtime proves they are defects.

    ## 3DS image handling
    - Confirm NCSD/NCCH structure before assuming partition layout.
    - NCCH metadata fields previously confused in practice: partition ID at offset `0x108`, program ID at `0x118` in the inspected NCCH header. Revalidate against the target game/tooling before using these values operationally.
    - Preserve non-target partitions byte-for-byte when only partition 0/RomFS is modified.
    - Never edit source ROM in-place.

    ## RomFS-first policy
    Start with RomFS-only. Touch ExeFS/code only if a controlled test proves RomFS cannot provide the needed behavior.

    ## Output verification
    A successful packer exit code is insufficient. Re-extract the output RomFS and SHA-256 every patched file against the patch manifest before reporting build success.
    """)

    write("03_BUILDER/LOCAL_FALLBACK_RULE.md", r"""
    # Execution Environment Fallback Rule
    Distinguish project failure from execution-environment failure.

    Environment failures include backend timeout, unavailable compiler, OS mismatch, missing system dependency, sandbox limits, memory/time limits, or inability to produce a Windows binary.

    Response:
    1. Keep the technical method and current baseline unchanged.
    2. Package the exact command/scripts/tools/config/input placeholders into `LOCAL_EXECUTION_PACKAGE`.
    3. Add one-click `run.bat` where possible.
    4. Auto-record environment, tool versions, hashes, command output, stage, traceback, and file inventory.
    5. User returns one `FAILURE_BUNDLE.zip` if it fails.
    6. Do not restart reverse engineering merely because the cloud runner failed.
    """)

    write("04_RUNTIME_QA/RUNTIME_QA_PLAYBOOK.md", r"""
    # Runtime QA Playbook

    QA verifies behavior; QA is not expected to reverse engineer binaries.

    Always record GAME VERSION, BUILD ID, scene/location, screenshot, reproduction steps, expected/actual result, severity, regression status, and last known good build.

    Check at minimum:
    - untranslated visible text;
    - clipping/overflow;
    - wrong alignment;
    - disconnected Arabic glyphs;
    - reversed words or line order;
    - mixed Arabic/Latin/number direction errors;
    - punctuation/order problems;
    - missing glyph/tofu;
    - wrong text color/style/contrast;
    - localized graphics/badges/icons;
    - dialogue paging and choices;
    - menus, lists, save/load, shops, inventory, tutorials;
    - crashes/freezes;
    - regression in previously accepted screens.

    A screenshot should include enough surrounding UI to identify the resource and presentation context.
    """)

    write("04_RUNTIME_QA/BUG_REPORT_TEMPLATE.md", r"""
    # Runtime Bug Report
    GAME VERSION:
    BUILD ID:
    SCENE / LOCATION:
    SCREENSHOT:
    EXPECTED:
    ACTUAL:
    REPRODUCTION STEPS:
    SEVERITY: BLOCKER / HIGH / MEDIUM / LOW
    REGRESSION: YES / NO / UNKNOWN
    LAST KNOWN GOOD BUILD:
    FILES LIKELY INVOLVED: [optional; QA may leave UNKNOWN]
    NOTES:
    """)

    write_csv("04_RUNTIME_QA/REGRESSION_MATRIX_TEMPLATE.csv", [
        ["test_id", "area", "scene", "expected", "baseline_build", "current_build", "result", "screenshot", "notes"],
        ["QA-001", "dialogue/menu/mixed/layout/graphics", "", "", "", "", "PASS/FAIL", "", ""],
    ])

    write("05_EXTRACTION/NEW_GAME_DISCOVERY_PROTOCOL.md", r"""
    # New Game Discovery Protocol

    Goal: identify **what differs from the known pipeline**, not relearn 3DS localization from zero.

    Record:
    - title, region, revision/update/DLC state;
    - source file type, size, SHA-256;
    - NCSD/NCCH partitions and IDs;
    - ExeFS/RomFS inventory;
    - likely text archives and their magic/structure;
    - fonts and font format;
    - layout/texture formats;
    - compression/encryption wrappers;
    - existing Unicode/Arabic glyph support;
    - renderer behavior for Arabic, combining forms, RTL, numbers, punctuation;
    - whether the reusable RomFS overlay patcher applies.

    Stop discovery as soon as each unknown has enough evidence to route a concrete PoC. Do not perform broad research unrelated to observed formats.
    """)

    write("05_EXTRACTION/3DS_CONTAINER_DISCOVERY_CHECKLIST.md", r"""
    # 3DS Container Discovery Checklist
    - [ ] preserve source copy read-only
    - [ ] SHA-256 and exact byte size
    - [ ] NCSD magic at expected location for .3ds/.cci source
    - [ ] partition count and non-empty partition indexes
    - [ ] partition ID and program ID recorded independently
    - [ ] product code / title metadata recorded
    - [ ] ExeFS inventory + `.code` hash
    - [ ] RomFS inventory + file count
    - [ ] candidate text/font/layout archives sampled by magic and size
    - [ ] update/DLC priority determined from actual files/runtime configuration, not assumption
    - [ ] no write performed during discovery
    """)

    write("06_TEXT_PIPELINE/TEXT_PIPELINE_GATES.md", r"""
    # Text Pipeline Gates

    ## Gate T1 — Extraction
    Extract all records with stable IDs/labels and preserve binary metadata required for rebuild.

    ## Gate T2 — No-op rebuild
    Extract -> serialize -> deserialize -> rebuild with no translation. Best result: byte-identical. If not byte-identical, require strict structural validity and explain deterministic binary differences.

    ## Gate T3 — Structural audit
    Validate archive bounds, entry offsets/sizes, alignments, overlap/truncation, unknown fields, block sizes, string tables, offsets, dummy/trailing records, and any format-specific invariants discovered.

    ## Gate T4 — Token safety
    Build token inventory from the target game. Validate per record/entry, not only globally. Structural tokens preserve sequence; movable dynamic placeholders preserve exact spelling/count. Unknown token classes default to conservative exact sequence/count.

    ## Gate T5 — Arabic transform
    Translator source remains natural Arabic. Build stage performs the game's approved shaping/RTL transform while protecting tokens.

    ## Gate T6 — Wrapping
    Apply final wrapping only after measuring the actual font and presentation constraints. Test dialogue, menus, lists, choices, mixed text, and narrow labels.

    ## Gate T7 — Rebuild + re-extract verification
    Rebuild, extract again, compare translated records, tokens, and structural metadata.
    """)

    write("06_TEXT_PIPELINE/CONTROL_CODES_POLICY.md", r"""
    # Control Code and Placeholder Policy

    Proven engineering lesson: global token counts are insufficient. Validation must operate at the smallest stable record identity (archive / subarchive / entry / label where available).

    Categories:
    1. **Dynamic placeholders** — may move for grammar if explicitly classified; exact spelling and multiplicity are mandatory.
    2. **Structural/control tags** — preserve spelling, count, and usually sequence.
    3. **Style spans** — preserve source-relative semantics; do not auto-balance malformed source spans without proof.
    4. **Unknown** — conservative exact count + exact sequence until understood.

    Completed-project examples included page/position/face/font/speed controls, player/item/character variables, and paired color tags. These spellings are examples only; inventory the new game independently.
    """)

    write("06_TEXT_PIPELINE/WRAPPING_POLICY.md", r"""
    # Wrapping Policy
    - Do not assume character count equals rendered width.
    - Measure using the final font metrics or a runtime-calibrated approximation.
    - Protect control tags/placeholders from splitting.
    - Preserve explicit page/line controls unless a deliberate rewrite changes them.
    - Test mixed Arabic/Latin/numbers separately.
    - Translator writes natural Arabic; wrapping is a build concern after linguistic text is approved.
    - Exact transform/wrap ordering is game-specific and must be proven by the Arabic PoC before scaling.
    """)

    write("07_ARABIC_FONT/BFFNT_WORKFLOW.md", r"""
    # Arabic Font / BFFNT Workflow

    Status: **PARTIALLY REUSABLE**.

    A donor Arabic BFFNT approach was Runtime-proven in the completed project, but the donor binary is game content and is not distributed here. Do not assume another game can use the same font unchanged.

    Workflow:
    1. Identify all fonts actually used by the target game and variants/styles.
    2. Dump font structure, glyph maps, texture sheets, CWDH/CMAP/metrics, encoding, and renderer expectations.
    3. Determine whether Arabic code points already exist.
    4. Prefer extending/replacing glyph coverage while preserving the target game's metric conventions.
    5. Do not globally change width metrics merely to solve one small UI defect.
    6. Build a minimal Arabic glyph PoC containing joining forms needed by the approved shaping method.
    7. Test dialogue, menu, small text, dark/light backgrounds, mixed text, numerals.
    8. Freeze the font once Runtime-approved; reopen only with evidence of a font-specific defect.

    Completed-project reference: final main/sub fonts were byte-identical and Runtime validated after replacement. Use the baseline manifest only as historical evidence, not as a transplantable asset.
    """)

    write("07_ARABIC_FONT/FONT_DIAGNOSTIC_TREE.md", r"""
    # Font Diagnostic Tree
    Missing glyph/tofu?
    -> Confirm code point emitted by build.
    -> Confirm CMAP/glyph mapping contains it.
    -> Confirm atlas sheet contains glyph.
    -> Confirm glyph index/texture coordinates.

    Glyph exists but spacing wrong?
    -> CWDH/advance/bearing/metric issue.
    -> Check whether defect is global or one layout box before changing metrics.

    Glyph shape wrong?
    -> shaping form/mapping vs atlas art.

    Text visible but unreadable?
    -> test size, contrast, pane color/style, raster resolution, scaling/filtering.

    Works in one font style only?
    -> locate all font variants and style-specific resources.
    """)

    write("08_RTL_AND_RENDERING/ARABIC_RENDERING_WORKFLOW.md", r"""
    # Arabic Rendering Workflow

    Status: **PARTIALLY REUSABLE**.

    Completed-project principle that should be retained: translators author normal Arabic; shaping and RTL/BiDi are automated in the build stage.

    New-game PoC must determine:
    - whether renderer shapes Arabic natively;
    - whether stored text must be presentation forms;
    - whether the engine performs any BiDi reordering itself;
    - line-level vs paragraph-level reordering behavior;
    - treatment of numbers, punctuation, Latin segments, variables, icons, and control tags.

    Protect control tokens with sentinels before shaping/reordering and restore them afterward. Test token adjacency explicitly.

    Do not double-apply BiDi. If the renderer already reorders, pre-reordering may reverse the result again.
    """)

    write("08_RTL_AND_RENDERING/MIXED_DIRECTION_RULES.md", r"""
    # Mixed Direction Test Set
    Every Arabic renderer PoC must include:
    - Arabic only;
    - Arabic + Western digits;
    - Arabic + Latin acronym/name;
    - Arabic + placeholder token;
    - Arabic + parentheses;
    - Arabic + colon/slash/percent;
    - positive/negative values;
    - item quantity patterns;
    - multi-line dialogue;
    - menu label with icon/button hint.

    Judge Runtime output, not console/log appearance.
    """)

    write("09_BUILD_AND_REINSERTION/BUILD_PIPELINE.md", r"""
    # Build and Reinsertion Pipeline
    1. Verify source hash against project manifest.
    2. Build translated text from approved source records.
    3. Validate tokens/placeholders before binary insertion.
    4. Apply shaping/RTL/wrapping according to the locked game profile.
    5. Repack text archives and run strict structural audit.
    6. Stage font/layout/graphics modifications from named baselines.
    7. Overlay only changed RomFS files into an extracted working copy.
    8. Rebuild the target NCCH/partition while preserving non-target partitions.
    9. Rebuild output ROM as a new file; never replace source.
    10. Re-extract output RomFS.
    11. SHA-256 every patched file against build manifest.
    12. Generate build report with changed/unchanged files and hashes.
    13. Send build to Runtime QA with exact build ID.
    """)

    write("09_BUILD_AND_REINSERTION/AH3P_FORMAT.md", r"""
    # AH3P Generic RomFS Patch Format

    Status: **REUSABLE when the game can be localized by RomFS overlay in partition 0**.

    `.ah3p` is an ordinary ZIP with:
    - `patch.json`
    - `romfs/<changed files>`

    Manifest records format/version, target type, patch identity, game name/title metadata, accepted source SHA-256 values, source size, output suffix, and SHA-256 of every overlay file.

    The completed generic Windows patcher validates the patch, validates the source `.3ds/.cci`, rebuilds partition 0 using a RomFS overlay, preserves other NCSD partitions, and re-extracts/verifies every patched file before success.

    Do not use AH3P unchanged when localization requires ExeFS/code patching, separate update/DLC containers, CIA-only workflows, encrypted content that the tool cannot process, or nonstandard container behavior. Extend the format explicitly instead of hiding extra operations.
    """)

    write("09_BUILD_AND_REINSERTION/REBUILD_VERIFICATION.md", r"""
    # Rebuild Verification
    PASS requires all of the following:
    - source accepted by exact size/hash policy;
    - patch manifest itself valid and safe from path traversal;
    - build tools exit successfully;
    - output is a valid expected container;
    - non-target partitions preserved where applicable;
    - output RomFS re-extracted;
    - every patched file present and SHA-256 equal to the staged payload;
    - output has a new filename and source remains unchanged;
    - build log retained on failure.
    """)

    write("10_VALIDATION/VALIDATION_GATES.md", r"""
    # Validation Gates
    **G0 Source** — immutable source, identity, hashes, inventory.
    **G1 Round-trip** — no-op extraction/rebuild proof.
    **G2 Structural** — binary structure and bounds.
    **G3 Token safety** — per-record control/placeholder validation.
    **G4 Arabic font** — glyph/mapping/metrics PoC.
    **G5 Arabic render** — shaping/RTL/mixed direction Runtime PoC.
    **G6 End-to-end** — one real translated string through final build.
    **G7 Scale build** — automated translation build with zero mechanical QA errors.
    **G8 Runtime regression** — representative screen matrix.
    **G9 Release** — clean rebuild, hashes, patch packaging, Runtime smoke, release manifest.
    """)

    write("10_VALIDATION/REUSABILITY_MATRIX.md", r"""
    # Reusability Matrix
    | Component | Status | Rule |
    |---|---|---|
    | SHA-256 source manifests | REUSABLE | use on every project |
    | No-op round-trip gate | REUSABLE | adapt parser/repacker to actual format |
    | Per-record token validation | REUSABLE | regenerate token inventory from new game |
    | Natural Arabic authoring | REUSABLE | build transforms remain technical |
    | Arabic reshaper/BiDi reference pipeline | PARTIALLY REUSABLE | prove renderer behavior first |
    | BFFNT donor strategy | PARTIALLY REUSABLE | revalidate format, glyph mapping, metrics, legal source |
    | Final completed-project BFFNT binary | GAME-SPECIFIC — REVALIDATE | not distributed |
    | XBB/PAPA parser assumptions | GAME-SPECIFIC — REVALIDATE | use only if new game has same format |
    | Corrected NCCH ID-offset lesson | PARTIALLY REUSABLE | verify header/tool interpretation |
    | RGBA4 nibble order reference | PARTIALLY REUSABLE | only for Nintendo 3DS RGBA4 resource using same packing |
    | AH3P RomFS patcher | REUSABLE / CONDITIONAL | only for compatible `.3ds/.cci` RomFS-overlay targets |
    | ListSelect/badge/color fixes | GAME-SPECIFIC — REVALIDATE | engineering lessons reusable, resources are not |
    | code.bin untouched policy | REUSABLE decision rule | RomFS-first, code only with evidence |
    """)

    write("11_TESTING/POC_SEQUENCE.md", r"""
    # Minimal Proof-of-Concept Sequence
    POC-01 source extraction and inventory
    POC-02 text no-op rebuild
    POC-03 token corruption negative test
    POC-04 one Arabic glyph/font rendering
    POC-05 joining word + sentence RTL
    POC-06 mixed Arabic/Latin/digits/punctuation
    POC-07 one dialogue string
    POC-08 one menu/list string
    POC-09 choice/page/control-tag string
    POC-10 clean build -> output re-extraction -> file hash verification

    Scaling translation before POC-10 is an explicit Supervisor exception, not the default.
    """)

    write("11_TESTING/TEST_MATRIX.md", r"""
    # Regression Test Matrix
    Static:
    - source/hash check
    - parser structural tests
    - no-op rebuild
    - token validator negative tests
    - shaping/token protection tests
    - patch manifest safety/path traversal tests
    - build output per-file hashes

    Runtime:
    - opening/title
    - dialogue multi-page
    - choices
    - menu/list
    - item/shop/inventory
    - save/load
    - tutorials/help
    - mixed direction + numbers
    - narrow text
    - semantic colored text
    - localized texture/icon/badge
    - screens touched by latest change
    - representative previously frozen screens
    """)

    write("13_REFERENCE_FILES/FINAL_PROJECT_BASELINE.md", r"""
    # Completed Project Baseline — Reference Only

    These facts are retained to demonstrate what was actually proven. They are not assumptions for another game.

    - Target source image: USA `.3ds`, 1,073,741,824 bytes, SHA-256 `146cb1cc2d8c63cad81ced4e0a18b13672488dd52fd810501437e64934a1aab1`.
    - Text no-op round-trip was proven byte-identical on the original source text archive before translation.
    - Final localized `Msg.xbb` SHA-256: `4b6002f69d4b39ee63834fe16e88e24ad305708f33a06578f47939c9d3a6715e`.
    - Final localized `DataText.xbb` SHA-256: `0205ed487d4f29e6be61996f7c72174bf806ccdcb4a4ca1a1334ce42bba5b0e1`.
    - Final approved main/sub BFFNT SHA-256: `3fc950767ad7e93aff853a9426b7bd9f76ad02fcba410ac86fca599fda1c5521` each.
    - Final `Layout/ListSelect.arc` SHA-256: `413429d9121912596186c35f2119bfb0b1424dc23c41310e7eed5ab610ed18e2`.
    - Final Runtime10 localization bundle SHA-256: `9d4048c1451198c5158857951c7a998d735d546f971080b9b2659210a6f61c96`.
    - Final Runtime10 RomFS archive used by installer SHA-256: `f80c16c19973fbaa459b6542128fd0cb928eb37df62b06a99d012882328ff048`.
    - The final RomFS payload contained 71 files and output-build verification compared each patched file.
    - Generic patcher Windows EXE build SHA-256: `9e4049d5e67de28afc08f3b6bcfbf664d23d76f528d3aef48c3a4bc5b27db512`.
    - Generic Trio AH3P example SHA-256 from the final generic-patcher CI build: `f3cf7b12768eb45fc16884df33f6c29a9f2f058b44705e134a7cd03d62c42a6b`.
    - Final generic-patcher CI artifact ZIP SHA-256: `aa77d81bfa562cb33e0e460b9efee8f1bf487824ce16bf2523620511c2f1becf`.
    - `code.bin` remained untouched in the localization solution.

    Historical donor-font and localized game binaries are not included because they are game content and not generically reusable.
    """)

    write_csv("10_VALIDATION/KNOWN_GOOD_BASELINE.csv", [
        ["component", "final_version", "file", "sha256", "purpose", "dependencies", "status", "reusability", "notes"],
        ["Source ROM identity", "completed-project", "Story of Seasons - Trio of Towns (USA).3ds", "146cb1cc2d8c63cad81ced4e0a18b13672488dd52fd810501437e64934a1aab1", "source validation reference", "none", "VERIFIED", "GAME-SPECIFIC — REVALIDATE", "do not distribute ROM"],
        ["Localized message archive", "Runtime10", "Msg.xbb", "4b6002f69d4b39ee63834fe16e88e24ad305708f33a06578f47939c9d3a6715e", "final localized text", "game parser/repacker", "VERIFIED", "GAME-SPECIFIC — REVALIDATE", "hash reference only"],
        ["Localized data text", "Runtime10", "DataText.xbb", "0205ed487d4f29e6be61996f7c72174bf806ccdcb4a4ca1a1334ce42bba5b0e1", "final visible data strings", "game format", "VERIFIED", "GAME-SPECIFIC — REVALIDATE", "hash reference only"],
        ["Arabic main font", "Runtime approved", "Font/mainfont.bffnt", "3fc950767ad7e93aff853a9426b7bd9f76ad02fcba410ac86fca599fda1c5521", "Arabic glyph rendering", "BFFNT renderer", "VERIFIED RUNTIME", "GAME-SPECIFIC — REVALIDATE", "binary not included"],
        ["Arabic sub font", "Runtime approved", "Font/subfont.bffnt", "3fc950767ad7e93aff853a9426b7bd9f76ad02fcba410ac86fca599fda1c5521", "Arabic glyph rendering", "BFFNT renderer", "VERIFIED RUNTIME", "GAME-SPECIFIC — REVALIDATE", "binary not included"],
        ["ListSelect layout archive", "Runtime10", "Layout/ListSelect.arc", "413429d9121912596186c35f2119bfb0b1424dc23c41310e7eed5ab610ed18e2", "final UI fixes", "game layout format", "VERIFIED RUNTIME", "GAME-SPECIFIC — REVALIDATE", "binary not included"],
        ["RomFS payload archive", "Runtime10 installer payload", "romfs.rar", "f80c16c19973fbaa459b6542128fd0cb928eb37df62b06a99d012882328ff048", "71-file localization payload", "final files", "VERIFIED BUILD", "GAME-SPECIFIC — REVALIDATE", "not included"],
        ["Generic patch engine", "AH3P v1", "universal_3ds_patcher/engine.py", "see source snapshot", "generic safe RomFS overlay patching", "3dstool, Windows", "VERIFIED BUILD", "REUSABLE / CONDITIONAL", "source included"],
        ["Generic patch builder", "AH3P v1", "universal_3ds_patcher/make_patch.py", "see source snapshot", "create patch.json + romfs ZIP", "Python", "VERIFIED BUILD", "REUSABLE / CONDITIONAL", "source included"],
    ])

    write("13_REFERENCE_FILES/UPSTREAM_REFERENCES.md", r"""
    # Upstream References
    - Story of Seasons: Trio of Towns fan-translation tooling used as a basis during the completed project: `mirusu400/Story-of-seasons-Trio-of-Towns-Fan-Translation`.
    - `3dstool` was used by the final Windows installer/build workflow for 3DS image extraction/rebuilding.
    - `arabic-reshaper` and `python-bidi` are useful reference libraries for build-time Arabic transformation, subject to renderer PoC.

    Always record the exact commit/tool version used by a new project. Do not rely on branch names alone.
    """)

    write("14_FAILURE_CASES/FAILURE_PREVENTION_GUIDE.md", r"""
    # Failure-Prevention Guide

    ## 1. Semantic text looks correct but rebuilt binary is structurally invalid
    **SYMPTOM:** extracted strings compare equal; game/archive still fails or strict parser reports corruption.
    **ROOT CAUSE:** binary metadata such as block sizes, offsets, alignments, bounds, unknown fields, dummy records, or tables was not preserved/recomputed correctly.
    **IDENTIFY EARLY:** strict no-op round-trip audit with deliberate corruption regression tests.
    **DO NOT REPEAT:** validating only JSON/text equality.
    **WORKING APPROACH:** structural parser + semantic comparison; require both valid and equal as appropriate.
    **VALIDATE:** no-op rebuild, structure audit, then Runtime.
    **APPLIES:** every proprietary text/archive format.
    **DOES NOT APPLY:** plain text resources with no binary structure.

    ## 2. Control tags survive globally but move/disappear in individual strings
    **SYMPTOM:** total token counts match, but pages/faces/variables break in specific dialogue.
    **ROOT CAUSE:** global counter validation.
    **IDENTIFY EARLY:** per-record token inventory and negative tests.
    **DO NOT REPEAT:** compare aggregate counts only.
    **WORKING APPROACH:** validate by stable record identity; structural controls preserve sequence, dynamic placeholders preserve exact spelling/count, unknown tags use conservative exact sequence/count.
    **VALIDATE:** source->source identity and intentional deletion/reordering negative tests.
    **APPLIES:** tagged/variable game text.

    ## 3. Source anomaly is "fixed" automatically
    **SYMPTOM:** validator or builder modifies an unbalanced style/control pattern present in the original.
    **ROOT CAUSE:** assuming source is syntactically ideal.
    **IDENTIFY EARLY:** inventory exceptions from untouched source.
    **DO NOT REPEAT:** auto-insert closing tags or normalize unknown controls.
    **WORKING APPROACH:** source-relative exception list; preserve until Runtime evidence proves a defect.
    **VALIDATE:** compare translated record against source policy.

    ## 4. Arabic is reversed twice or joins break
    **SYMPTOM:** words reverse, numbers jump, or contextual forms are wrong.
    **ROOT CAUSE:** applying shaping/BiDi without proving renderer behavior; double reordering; tokens participating in BiDi.
    **IDENTIFY EARLY:** minimal Arabic/mixed-direction Runtime PoC.
    **DO NOT REPEAT:** manually reverse translation text or blindly apply a generic RTL function.
    **WORKING APPROACH:** natural Arabic source; protect tokens; apply only the transform proven for this renderer.
    **VALIDATE:** Arabic-only + mixed Latin/digits/punctuation + multi-line Runtime set.

    ## 5. Font change fixes one screen but damages many others
    **SYMPTOM:** one label improves; spacing/wrapping globally regresses.
    **ROOT CAUSE:** global metric/CWDH modification for a local presentation issue.
    **IDENTIFY EARLY:** compare defect scope across multiple UI contexts.
    **DO NOT REPEAT:** global metric edits without evidence.
    **WORKING APPROACH:** preserve approved font metrics; target the layout/string/texture when defect is local.
    **VALIDATE:** representative font regression matrix.

    ## 6. Tiny localized graphic is readable in source image but unreadable in Runtime
    **SYMPTOM:** badge/icon lettering collapses after in-game scaling/filtering.
    **ROOT CAUSE:** designing at file resolution rather than actual presentation size.
    **IDENTIFY EARLY:** Runtime screenshot at real scale after first PoC.
    **DO NOT REPEAT:** endless redraws inside a proven-too-small fixed box.
    **WORKING APPROACH:** if wording cannot be shortened and the box is the limit, adjust presentation/layout dimensions rather than only the texture.
    **VALIDATE:** real Runtime readability, not PNG preview.

    ## 7. RGBA4 texture colors/channels are wrong
    **SYMPTOM:** decoded/re-encoded texture has swapped or corrupted colors/alpha.
    **ROOT CAUSE:** incorrect nibble packing assumption.
    **IDENTIFY EARLY:** round-trip known pixels and channel-pattern test image.
    **DO NOT REPEAT:** generic RGBA4444 byte order without checking platform/resource packing.
    **WORKING APPROACH from completed project:** for the proven Nintendo 3DS RGBA4 resource, byte0 was `RRRRAAAA`, byte1 `BBBBGGGG`.
    **VALIDATE:** pixel round-trip + Runtime texture.
    **APPLIES:** only when the target resource is confirmed to use the same RGBA4 packing.

    ## 8. Wrong UI text color applied too broadly
    **SYMPTOM:** readability improves in one menu but semantic red/blue/green indicators lose meaning.
    **ROOT CAUSE:** global color replacement.
    **IDENTIFY EARLY:** classify ordinary/default text panes separately from semantic/status panes.
    **DO NOT REPEAT:** blanket RGBA substitution.
    **WORKING APPROACH:** targeted pane/resource list; preserve semantic colors.
    **VALIDATE:** screenshots across default and semantic states.

    ## 9. NCCH metadata fields are misread
    **SYMPTOM:** partition/program IDs appear contradictory and routing decisions become wrong.
    **ROOT CAUSE:** confusing header offsets/field meaning.
    **IDENTIFY EARLY:** test parser with deliberately different values and compare to trusted tooling/spec.
    **DO NOT REPEAT:** assume similar-looking ID fields are interchangeable.
    **WORKING REFERENCE:** completed-project extractor correction distinguished partition ID at `0x108` and program ID at `0x118`.
    **VALIDATE:** unit test + real partition inventory.

    ## 10. Installer says success but localization is incomplete
    **SYMPTOM:** generated ROM launches but some expected modified resources are absent/old.
    **ROOT CAUSE:** checking build process only, not the rebuilt output contents.
    **IDENTIFY EARLY:** output re-extraction and per-file manifest verification.
    **DO NOT REPEAT:** trust packer exit code alone.
    **WORKING APPROACH:** hash every payload file, rebuild, re-extract, hash every corresponding output file, fail on any mismatch.
    **VALIDATE:** 100% manifest match before success UI.

    ## 11. Update/DLC explanation is assumed without evidence
    **SYMPTOM:** incomplete localization is attributed to update precedence before inspecting actual source/runtime layers.
    **ROOT CAUSE:** reasoning from expected platform behavior instead of the concrete build.
    **IDENTIFY EARLY:** inventory exact source, installed update/DLC state, emulator/mod layers, and output resource hashes.
    **DO NOT REPEAT:** diagnose overlay precedence without file evidence.
    **WORKING APPROACH:** first prove whether the expected file exists in the output and what layer Runtime reads.

    ## 12. Attempting to edit a Windows EXE with WinRAR/7-Zip because it "looks like an installer"
    **SYMPTOM:** archive tool reports no archive or cannot replace payload.
    **ROOT CAUSE:** assuming packaging technology.
    **IDENTIFY EARLY:** inspect PE, overlay, resources, PyInstaller/Inno/NSIS signatures before choosing tooling.
    **DO NOT REPEAT:** blind SFX manipulation.
    **WORKING APPROACH:** identify actual container; the successful reference installer was PyInstaller and its payload/tooling was extracted and recreated accordingly.

    ## 13. Execution backend failure stalls engineering
    **SYMPTOM:** TransportTimeoutError, unavailable compiler, sandbox limitation.
    **ROOT CAUSE:** treating environment availability as proof the method failed.
    **IDENTIFY EARLY:** distinguish command/tool failure from infrastructure exception.
    **DO NOT REPEAT:** restart research or declare project failure.
    **WORKING APPROACH:** move build to GitHub Actions or packaged local execution; preserve logs and hashes.

    ## 14. Reopening solved components causes regression
    **SYMPTOM:** a targeted defect triggers changes to text/font/wrapping/code simultaneously.
    **ROOT CAUSE:** no freeze/baseline discipline.
    **IDENTIFY EARLY:** task does not name implicated layer and protected files.
    **DO NOT REPEAT:** multi-subsystem speculative edits.
    **WORKING APPROACH:** one owner, one objective, explicit DO NOT CHANGE list, minimal delta, targeted regression tests.
    """)

    write("14_FAILURE_CASES/FAILURE_SIGNATURES.md", r"""
    # Failure Signatures
    - `papa_block_size_mismatch` -> structural rebuild defect; do not accept semantic equality alone.
    - Wrong-source SHA/size -> stop before extraction/patching.
    - Patched-file hash mismatch after output re-extraction -> integration/rebuild failure, not translation failure.
    - Missing glyph/tofu with correct Arabic bytes -> font mapping/atlas likely; verify before blaming shaping.
    - Correct glyphs but reversed order -> BiDi/render order likely; verify renderer transform policy.
    - Correct text in archive but English in Runtime -> wrong resource/layer/build stale; trace resource actually loaded.
    - Only tiny badge unreadable while font text is fine -> localized raster/layout presentation issue.
    - Tool works locally but cloud times out -> environment blocker; use local/CI fallback package.
    """)

    write("15_PROMPT_LIBRARY/01_NEW_SUPERVISOR_MASTER_PROMPT.txt", f"""
    You are the Supervisor of a Nintendo 3DS Arabic localization project. Your job is to coordinate evidence-based execution, not to perform every specialist task yourself.

    Read the Knowledge Pack before routing work. Treat the new game as different unless a format is proven identical.

    CORE RULES
    - Maintain one authoritative PROJECT CONTROL state.
    - Route linguistic tasks to Translator, binary/build/font/rendering tasks to Builder, in-game verification to Runtime QA, sequencing/evidence/freeze decisions to Supervisor.
    - Never issue vague tasks. Every task must name exact files, evidence, constraints, success criteria, and required return artifacts.
    - Mark technical conclusions VERIFIED / LIKELY / UNKNOWN.
    - Protect known-good components. Do not reopen a frozen subsystem without evidence.
    - Never confuse execution-environment failure with project failure. Move the same task to CI or a local execution package when needed.
    - Do not scale translation before no-op reinsertion, token safety, Arabic font/rendering PoC, and one end-to-end Runtime string pass.
    - Do not claim Runtime testing unless the game actually ran.
    - Keep source files immutable and use SHA-256 manifests.
    - Prefer RomFS-only; edit ExeFS/code only if an actual test proves it is required.

    ATTACHMENTS REQUIRED:
    YES for project intake: source manifest/hash report and the smallest legal-safe structural/extracted package available. Do not request a ROM if the team already has an accessible verified source. For delegated tasks, follow the attachment matrix.

    {COMMON_TASK_FORMAT}
    """)

    write("15_PROMPT_LIBRARY/02_TRANSLATOR_MASTER_PROMPT.txt", r"""
    You are the Translator / Localization Engineer for a Nintendo 3DS Arabic localization project.

    Write Arabic in natural reading order. Do not manually reverse or pre-shape text. Preserve all control tags, placeholders, escape sequences, variables, and non-visible internal identifiers according to the Builder's token policy. Translate only records proven user-visible or explicitly approved.

    Maintain terminology consistency through the glossary. Use speaker/scene/menu/item context. Flag uncertain context rather than inventing. When wording does not fit a proven UI constraint, return a concise constraint report and alternatives; do not silently damage meaning.

    For mixed Arabic/Latin/numbers/punctuation, preserve required ASCII/variables and flag the record for Runtime mixed-direction testing.

    ATTACHMENTS REQUIRED:
    YES. Attach the translation worksheet/export containing stable record IDs, source text, current Arabic text, tokens/placeholders, context fields, and the approved glossary. If a Runtime wording defect is being fixed, also attach the screenshot and build ID.

    RETURN:
    updated translation file, glossary changes, list of intentionally untranslated records, uncertainty list, and a concise changelog keyed by stable record ID.
    """)

    write("15_PROMPT_LIBRARY/03_BUILDER_MASTER_PROMPT.txt", r"""
    You are the Builder / Integration Engineer for a Nintendo 3DS Arabic localization project. Operate as a ROM-hacking engineer.

    Use actual files before assumptions. Preserve immutable originals. Hash important inputs/outputs. Prove extraction and no-op reinsertion before translation scale. Validate proprietary binary structure, not only decoded text. Build per-record control-token safety before modifying strings. Keep translators' Arabic natural-order and automate the renderer-specific shaping/RTL/wrapping transform in the build stage.

    Treat font, text archive, layout/texture, RomFS build, ExeFS/code, and installer/patch format as separate subsystems. Change the minimum subsystem supported by evidence. Prefer RomFS-only until proven insufficient.

    Every build must be reproducible. Re-extract final output and SHA-256 every patched resource against the build/patch manifest before reporting success. Preserve non-target NCSD partitions. Never modify the selected source ROM in-place.

    If cloud/backend execution fails, prepare or use the Local Execution package; do not restart technical research.

    ATTACHMENTS REQUIRED:
    YES. Exact requirements depend on task: source/extracted target file, current modified file, relevant parser/repacker scripts, hashes, build manifest, and failure logs. For binary comparison, attach both original and modified copies. For font/layout/texture Runtime defects, attach screenshots and the exact resource archive(s).

    RETURN:
    changed files, unchanged protected files, before/after hashes, scripts/diffs, automated test results, build log, and exact Runtime handoff.
    """)

    write("15_PROMPT_LIBRARY/04_RUNTIME_QA_MASTER_PROMPT.txt", r"""
    You are the Runtime QA Tester for a Nintendo 3DS Arabic localization project.

    Your job is to run the provided build and report observed behavior. Do not diagnose binary internals unless explicitly assigned. Always include build ID and scene/location.

    Check untranslated text, clipping, overflow, alignment, broken Arabic joining, reversed text, mixed-direction ordering, punctuation, missing glyphs, wrong colors/styles, localized graphics/badges, crashes/freezes, and regressions in previously approved screens.

    ATTACHMENTS REQUIRED:
    YES. You need the exact build/patch under test plus the regression checklist. Return screenshots for failures and, when practical, representative pass screens for newly changed systems.

    RETURN:
    standardized bug reports with GAME VERSION, BUILD ID, SCENE / LOCATION, SCREENSHOT, EXPECTED, ACTUAL, REPRODUCTION STEPS, SEVERITY, REGRESSION, LAST KNOWN GOOD BUILD, and any reliable resource hint.
    """)

    task_prompts = {
        "05_NEW_GAME_DISCOVERY_PROMPT.txt": ("BUILDER / INTEGRATION ENGINEER", "Determine only what differs from the known reusable pipeline for the new 3DS game.", "YES", "Source identity manifest (filename, size, SHA-256), legal-safe partition/RomFS/ExeFS inventory or access to the verified source image, any already-extracted candidate text/font/layout files.", "Inspect container/partition structure, text/archive formats, fonts, renderer behavior, compression, layout/texture formats, update/DLC layers, and whether AH3P RomFS overlay patching applies. Mark each module REUSABLE / PARTIALLY REUSABLE / GAME-SPECIFIC — REVALIDATE. Do not begin translation."),
        "06_TEXT_EXTRACTION_TASK.txt": ("BUILDER / INTEGRATION ENGINEER", "Prove lossless extraction and no-op reinsertion for the primary text resource.", "YES", "Original target text/archive binary, current parser/repacker source, format notes if any, source SHA-256 manifest.", "Extract with stable record IDs and metadata, rebuild without translation, run byte/structural/semantic comparison, add corruption negative tests, and return scripts + hashes + audit report."),
        "07_FONT_ANALYSIS_TASK.txt": ("BUILDER / INTEGRATION ENGINEER", "Determine the target game's font structure and minimum Arabic glyph strategy.", "YES", "Original font file(s), renderer/layout samples that reference them, one screenshot showing normal font use, any existing font tools.", "Inventory mapping/metrics/atlas/variants, test Arabic coverage, create a minimal legal-safe PoC plan, and do not globally alter metrics without evidence."),
        "08_ARABIC_RENDERING_TASK.txt": ("BUILDER / INTEGRATION ENGINEER", "Prove the exact shaping/RTL policy required by the target renderer.", "YES", "Working text reinsertion build, working or PoC Arabic-capable font, mixed-direction test strings, relevant token policy, Runtime test access.", "Test natural Arabic, shaping only, BiDi combinations as needed; protect tokens; include Arabic+Latin+digits+punctuation+multiline. Return the one approved transform profile and Runtime evidence."),
        "09_REINSERTION_TASK.txt": ("BUILDER / INTEGRATION ENGINEER", "Reinsert approved translated records without structural or token regressions.", "YES", "Original archive, translated export with stable IDs, token policy/config, final parser/repacker, known-good baseline hash.", "Validate tokens before rebuild, rebuild archive, strict structural audit, re-extract and compare translated records, output changed/unchanged hashes."),
        "10_BUILD_TASK.txt": ("BUILDER / INTEGRATION ENGINEER", "Create a reproducible game build from the current frozen baseline and staged localization payload.", "YES", "Verified source image or build-access path, staged changed RomFS files, build manifest, required tools, protected baseline list.", "Build to a new output file, preserve non-target partitions, re-extract output, hash every changed file, retain failure log, and return build ID + exact QA handoff."),
        "11_RUNTIME_BUG_REPORT_TASK.txt": ("RUNTIME QA TESTER", "Reproduce and document one observed Runtime localization defect without speculative binary diagnosis.", "YES", "Exact build under test, regression checklist, previous known-good build if regression is suspected.", "Return standardized bug report, screenshot, reproduction steps, severity, regression status, and last-known-good build."),
        "12_REGRESSION_TEST_TASK.txt": ("RUNTIME QA TESTER", "Run focused regression coverage after a targeted fix.", "YES", "New build, immediately previous known-good build, list of files changed, expected effect, regression matrix.", "Test the fixed screen plus systems sharing the changed subsystem; return PASS/FAIL matrix and screenshots for failures."),
        "13_FINAL_RELEASE_VALIDATION.txt": ("SUPERVISOR", "Authorize or reject a release candidate using static, build, and Runtime evidence.", "YES", "Release candidate patch/build, source/patch hashes, build report, per-file output verification, Runtime smoke/regression results, open-defect list.", "Require clean-source reproducibility, correct source rejection, patch/output integrity, no unintended subsystem changes, Runtime smoke, and documented known limitations. Never infer Runtime pass from CI."),
    }
    for name, (role, obj, req, attachments, task) in task_prompts.items():
        write("15_PROMPT_LIBRARY/" + name, f"""
        TARGET ROLE:
        {role}

        OBJECTIVE:
        {obj}

        ATTACHMENTS REQUIRED:
        {req}

        ATTACHMENTS:
        {attachments}

        TASK:
        {task}

        SUCCESS CRITERIA:
        Evidence is reproducible; all stated validations pass; unknowns remain explicitly UNKNOWN rather than guessed.

        RETURN TO SUPERVISOR:
        Exact output artifacts, hashes, test/log evidence, files changed/not changed, and next technical unknown if any.
        """)

    write("16_PROJECT_BOOTSTRAP/PROJECT_BOOTSTRAP.md", r"""
    # New Project Bootstrap Procedure
    1. Intake source/project files; freeze originals.
    2. Create project manifest with title/region/version/source hashes.
    3. Inventory structure and compare to Knowledge Pack.
    4. Mark modules REUSABLE / PARTIALLY REUSABLE / GAME-SPECIFIC — REVALIDATE.
    5. Create an UNKNOWN list only for differences.
    6. Route each unknown to the correct role with exact attachments.
    7. Prove text extraction/no-op reinsertion.
    8. Enable per-record token validator.
    9. Prove Arabic font rendering.
    10. Prove shaping/RTL/mixed direction.
    11. Run one end-to-end translated-string Runtime test.
    12. Lock/freeze the working pipeline.
    13. Scale translation in checkpoints.
    14. Build continuously with output re-extraction verification.
    15. Runtime QA continuously on changed + frozen areas.
    16. Generate generic patch package only after the game's build mode is proven.
    17. Final release validation from clean source.
    """)

    write("16_PROJECT_BOOTSTRAP/ATTACHMENT_MANIFEST.md", r"""
    # Attachment Manifest
    | Request type | Attachments required | Preferred packaging |
    |---|---|---|
    | New game discovery | source identity/hash manifest; partition/RomFS/ExeFS inventory; representative candidate text/font/layout files | `DISCOVERY_INPUT.zip` excluding ROM where possible |
    | Text extraction/repack | original archive binary; parser/repacker; format notes | `TEXT_FORMAT_POC.zip` |
    | Token/control issue | source + translated record export; token inventory/policy; validator log | `TOKEN_CASE.zip` |
    | Translation task | worksheet/export; glossary; context screenshots when needed | `TRANSLATION_BATCH_vNNN.zip` |
    | Font analysis | all used font variants; mapping/atlas dumps if available; screenshot | `FONT_POC_INPUT.zip` |
    | RTL/rendering | PoC font; test text; token policy; current build | `ARABIC_RENDER_POC.zip` |
    | Layout/texture defect | exact original and modified resource archive; screenshot; pane/texture identifiers if known | `UI_DEFECT_<id>.zip` |
    | Build failure | source manifest; build scripts/config; exact changed payload; full command log | `BUILD_FAILURE_BUNDLE.zip` |
    | Runtime bug | build ID; screenshot; reproduction; last known good build ID | `RUNTIME_DEFECT_<id>.zip` if multiple captures |
    | Regression test | new build; previous known-good build; changed-file manifest; test matrix | `REGRESSION_HANDOFF.zip` |
    | Local execution fallback | scripts/tools/config/input placeholders + run.bat + Arabic README | `LOCAL_EXECUTION_PACKAGE.zip` |
    """)

    write("16_PROJECT_BOOTSTRAP/ROLE_ROUTING_MATRIX.md", (OUT / "01_SUPERVISOR/ROLE_ROUTING_MATRIX.md").read_text(encoding="utf-8") if (OUT / "01_SUPERVISOR/ROLE_ROUTING_MATRIX.md").exists() else "")

    write("17_LOCAL_EXECUTION/README_AR.txt", r"""
    حزمة التنفيذ المحلي — قالب عام

    1. ماذا أشغل؟
       شغّل run.bat.

    2. أين أضع الملفات؟
       ضع الملفات المطلوبة بأسمائها المحددة داخل input\ كما يوضح input\REQUIRED_FILES.txt.

    3. ماذا يفترض أن يحدث؟
       تتحقق الأداة من الملفات والـSHA-256 ثم تنفذ المهمة المسجلة في config\task.json وتكتب السجل تلقائيًا.

    4. أين أجد الناتج؟
       داخل output\.

    5. ماذا أرسل للفريق إذا فشل؟
       أرسل الملف FAILURE_BUNDLE.zip الذي تنشئه الحزمة تلقائيًا.
    """)

    write("17_LOCAL_EXECUTION/run.bat", r"""
    @echo off
    setlocal
    cd /d "%~dp0"
    if not exist logs mkdir logs
    if not exist output mkdir output
    echo [%date% %time%] Local execution started>logs\launcher.log
    where py >nul 2>nul
    if errorlevel 1 (
      echo Python launcher not found.>>logs\launcher.log
      echo Python 3 is required for this generic template.
      goto :fail
    )
    py -3 scripts\local_runner.py 1>>logs\launcher.log 2>>&1
    if errorlevel 1 goto :fail
    echo Completed. See output\
    pause
    exit /b 0
    :fail
    echo Failed. Building FAILURE_BUNDLE.zip...
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\collect_failure.ps1
    echo Send FAILURE_BUNDLE.zip to the project team.
    pause
    exit /b 1
    """)

    write("17_LOCAL_EXECUTION/scripts/local_runner.py", r'''
    from __future__ import annotations
    import hashlib, json, os, platform, subprocess, sys
    from pathlib import Path

    ROOT = Path(__file__).resolve().parents[1]
    CFG = ROOT / "config" / "task.json"
    LOG = ROOT / "logs" / "local_runner.log"

    def sha256(p: Path):
        h=hashlib.sha256()
        with p.open("rb") as f:
            for b in iter(lambda:f.read(1024*1024), b""):
                h.update(b)
        return h.hexdigest()

    def log(s):
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as f: f.write(str(s)+"\n")

    def main():
        cfg=json.loads(CFG.read_text(encoding="utf-8"))
        log("platform="+platform.platform())
        log("python="+sys.version.replace("\n"," "))
        for item in cfg.get("required_inputs",[]):
            p=ROOT / "input" / item["name"]
            if not p.is_file(): raise RuntimeError("missing input: "+item["name"])
            d=sha256(p); log(f"input {p.name} size={p.stat().st_size} sha256={d}")
            exp=(item.get("sha256") or "").lower()
            if exp and d.lower()!=exp: raise RuntimeError("SHA-256 mismatch: "+item["name"])
        command=cfg.get("command")
        if not command:
            raise RuntimeError("config/task.json has no command. Builder must populate it for the concrete local task.")
        log("command="+repr(command))
        proc=subprocess.run(command, cwd=ROOT, shell=isinstance(command,str), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
        log(proc.stdout or "")
        log("exit="+str(proc.returncode))
        if proc.returncode: raise SystemExit(proc.returncode)
    if __name__=="__main__": main()
    ''')

    write("17_LOCAL_EXECUTION/scripts/collect_failure.ps1", r"""
    $ErrorActionPreference='SilentlyContinue'
    $root=Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
    $tmp=Join-Path $root '_failure_bundle'
    Remove-Item $tmp -Recurse -Force
    New-Item -ItemType Directory -Path $tmp | Out-Null
    Copy-Item (Join-Path $root 'logs') $tmp -Recurse -Force
    Copy-Item (Join-Path $root 'config') $tmp -Recurse -Force
    Get-ComputerInfo | Out-File (Join-Path $tmp 'environment.txt') -Encoding utf8
    Get-ChildItem (Join-Path $root 'input') -File | ForEach-Object {
      $h=Get-FileHash $_.FullName -Algorithm SHA256
      "$($_.Name)`t$($_.Length)`t$($h.Hash.ToLower())"
    } | Out-File (Join-Path $tmp 'input_hashes.txt') -Encoding utf8
    $zip=Join-Path $root 'FAILURE_BUNDLE.zip'
    Remove-Item $zip -Force
    Compress-Archive -Path (Join-Path $tmp '*') -DestinationPath $zip -Force
    Remove-Item $tmp -Recurse -Force
    """)

    write_json("17_LOCAL_EXECUTION/config/task.json", {
        "task_id": "REPLACE_ME",
        "description": "Builder populates this file for the concrete blocked task.",
        "required_inputs": [{"name": "REPLACE_ME.bin", "sha256": ""}],
        "command": "echo Replace config/task.json with the exact Builder command"
    })
    write("17_LOCAL_EXECUTION/input/REQUIRED_FILES.txt", "Builder must replace this file with exact required filenames and expected hashes for the concrete local task.")
    write("17_LOCAL_EXECUTION/output/.gitkeep", "")
    write("17_LOCAL_EXECUTION/logs/.gitkeep", "")


def build_scripts():
    write("12_SCRIPTS/hash_manifest.py", r'''
    #!/usr/bin/env python3
    """Create deterministic SHA-256 manifest for a file tree."""
    from pathlib import Path
    import argparse, hashlib, json

    def sha256(p):
        h=hashlib.sha256()
        with p.open('rb') as f:
            for b in iter(lambda:f.read(1024*1024), b''): h.update(b)
        return h.hexdigest()

    ap=argparse.ArgumentParser(); ap.add_argument('root'); ap.add_argument('-o','--out',default='HASH_MANIFEST.json')
    a=ap.parse_args(); root=Path(a.root).resolve()
    files=[]
    for p in sorted((x for x in root.rglob('*') if x.is_file()), key=lambda x:x.relative_to(root).as_posix().lower()):
        files.append({'path':p.relative_to(root).as_posix(),'size':p.stat().st_size,'sha256':sha256(p)})
    Path(a.out).write_text(json.dumps({'root':str(root),'file_count':len(files),'files':files},indent=2),encoding='utf-8')
    print(f'files={len(files)} manifest={a.out}')
    ''')

    write("12_SCRIPTS/compare_trees.py", r'''
    #!/usr/bin/env python3
    """Compare two directory trees by relative path, size and SHA-256."""
    from pathlib import Path
    import argparse, hashlib, json
    def sha(p):
        h=hashlib.sha256()
        with p.open('rb') as f:
            for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
        return h.hexdigest()
    def scan(root): return {p.relative_to(root).as_posix():(p.stat().st_size,sha(p)) for p in root.rglob('*') if p.is_file()}
    ap=argparse.ArgumentParser(); ap.add_argument('a'); ap.add_argument('b'); ap.add_argument('-o','--out',default='TREE_COMPARE.json'); x=ap.parse_args()
    a=Path(x.a).resolve(); b=Path(x.b).resolve(); A=scan(a); B=scan(b)
    keys=sorted(set(A)|set(B)); rows=[]
    for k in keys:
        status='MATCH' if A.get(k)==B.get(k) else ('ONLY_A' if k not in B else 'ONLY_B' if k not in A else 'DIFF')
        rows.append({'path':k,'status':status,'a':A.get(k),'b':B.get(k)})
    result={'match':all(r['status']=='MATCH' for r in rows),'rows':rows}
    Path(x.out).write_text(json.dumps(result,indent=2),encoding='utf-8'); print('match=',result['match'],'report=',x.out)
    raise SystemExit(0 if result['match'] else 1)
    ''')

    write("12_SCRIPTS/control_token_validator.py", r'''
    #!/usr/bin/env python3
    """Generic per-record control-token validator.

    Input JSON: list of {id, source, translated}. Policy JSON optionally lists
    movable prefixes/exact tokens. Unknown tokens default to strict sequence.
    """
    import argparse, collections, json, re, sys
    TOKEN_RE=re.compile(r'<[^<>\r\n]+>')
    def tokens(s): return TOKEN_RE.findall(s or '')
    def is_movable(t,policy):
        if t in policy.get('movable_exact',[]): return True
        return any(t.startswith(p) for p in policy.get('movable_prefixes',[]))
    ap=argparse.ArgumentParser(); ap.add_argument('records'); ap.add_argument('--policy'); ap.add_argument('-o','--out',default='TOKEN_VALIDATION.json'); a=ap.parse_args()
    rec=json.load(open(a.records,encoding='utf-8-sig')); policy=json.load(open(a.policy,encoding='utf-8-sig')) if a.policy else {}
    errors=[]
    for r in rec:
        st=tokens(r.get('source','')); tt=tokens(r.get('translated',''))
        sm=[t for t in st if is_movable(t,policy)]; tm=[t for t in tt if is_movable(t,policy)]
        ss=[t for t in st if not is_movable(t,policy)]; ts=[t for t in tt if not is_movable(t,policy)]
        if collections.Counter(sm)!=collections.Counter(tm): errors.append({'id':r.get('id'),'kind':'movable_count','source':sm,'translated':tm})
        if ss!=ts: errors.append({'id':r.get('id'),'kind':'strict_sequence','source':ss,'translated':ts})
    out={'records':len(rec),'errors':errors,'pass':not errors}
    json.dump(out,open(a.out,'w',encoding='utf-8'),ensure_ascii=False,indent=2); print(json.dumps({'records':len(rec),'error_count':len(errors),'pass':not errors}))
    raise SystemExit(0 if not errors else 1)
    ''')

    write_json("12_SCRIPTS/token_policy_template.json", {
        "movable_exact": ["<MOJI0>"],
        "movable_prefixes": ["<____ITEMNAME", "<_____MYNAME", "<CHARANAME"],
        "note": "Examples only. Regenerate from the new game's actual token inventory; unknown tokens default to strict sequence."
    })

    write("12_SCRIPTS/arabic_text_transform.py", r'''
    #!/usr/bin/env python3
    """Reference Arabic shaping/BiDi transform with protected <...> tokens.

    PARTIALLY REUSABLE: run a renderer PoC before using in production.
    Requires: arabic-reshaper, python-bidi.
    """
    import argparse, json, re
    import arabic_reshaper
    from bidi.algorithm import get_display
    TOKEN=re.compile(r'<[^<>\r\n]+>')
    def transform(text):
        saved=[]
        def repl(m):
            i=len(saved); saved.append(m.group(0)); return f'\uE000{i}\uE001'
        protected=TOKEN.sub(repl,text)
        shaped=arabic_reshaper.reshape(protected)
        visual=get_display(shaped)
        for i,t in enumerate(saved): visual=visual.replace(f'\uE000{i}\uE001',t)
        return visual
    ap=argparse.ArgumentParser(); ap.add_argument('input_json'); ap.add_argument('output_json'); ap.add_argument('--field',default='arabic_natural_order'); ap.add_argument('--out-field',default='arabic_render')
    a=ap.parse_args(); data=json.load(open(a.input_json,encoding='utf-8-sig'))
    for r in data: r[a.out_field]=transform(r.get(a.field,'') or '')
    json.dump(data,open(a.output_json,'w',encoding='utf-8'),ensure_ascii=False,indent=2)
    ''')

    write("12_SCRIPTS/visible_latin_detector.py", r'''
    #!/usr/bin/env python3
    """Flag visible Latin letters in translated records; produces review list, not automatic errors."""
    import argparse,json,re
    LATIN=re.compile(r'[A-Za-z]')
    TAG=re.compile(r'<[^<>]*>')
    ap=argparse.ArgumentParser(); ap.add_argument('records'); ap.add_argument('-o','--out',default='VISIBLE_LATIN_REVIEW.json'); ap.add_argument('--field',default='translated'); a=ap.parse_args()
    rows=json.load(open(a.records,encoding='utf-8-sig')); hits=[]
    for r in rows:
        s=TAG.sub('',r.get(a.field,'') or '')
        if LATIN.search(s): hits.append({'id':r.get('id'),'text':r.get(a.field,''),'note':'Review: may be legitimate name/unit/acronym/internal content.'})
    json.dump(hits,open(a.out,'w',encoding='utf-8'),ensure_ascii=False,indent=2); print('review_count=',len(hits))
    ''')

    write("12_SCRIPTS/ncsd_ncch_inventory_reference.py", r'''
    #!/usr/bin/env python3
    """Read-only reference inventory for basic NCSD partition/NCCH identity fields.

    This is a discovery helper, not a complete 3DS parser. Field interpretations
    must be cross-checked for the new game/toolchain.
    """
    from pathlib import Path
    import argparse, hashlib, json
    MEDIA=0x200
    def sha(p):
        h=hashlib.sha256()
        with p.open('rb') as f:
            for b in iter(lambda:f.read(4*1024*1024),b''): h.update(b)
        return h.hexdigest()
    ap=argparse.ArgumentParser(); ap.add_argument('rom'); ap.add_argument('-o','--out',default='PARTITION_INVENTORY.json'); a=ap.parse_args(); p=Path(a.rom)
    with p.open('rb') as f:
        f.seek(0x100); magic=f.read(4)
        if magic!=b'NCSD': raise SystemExit('not NCSD')
        f.seek(0x120); table=f.read(64)
        parts=[]
        for i in range(8):
            off=int.from_bytes(table[i*8:i*8+4],'little')*MEDIA; size=int.from_bytes(table[i*8+4:i*8+8],'little')*MEDIA
            if not off or not size: continue
            f.seek(off+0x100); nmagic=f.read(4)
            row={'index':i,'offset':off,'size':size,'ncch_magic':nmagic.decode('ascii','replace')}
            if nmagic==b'NCCH':
                f.seek(off+0x108); row['partition_id']=f.read(8).hex().upper()
                f.seek(off+0x118); row['program_id']=f.read(8).hex().upper()
                f.seek(off+0x150); row['product_code']=f.read(16).split(b'\0',1)[0].decode('ascii','replace')
            parts.append(row)
    out={'file':str(p.resolve()),'size':p.stat().st_size,'sha256':sha(p),'partitions':parts,'warning':'Read-only reference helper; confirm field endianness/semantics with target tooling.'}
    Path(a.out).write_text(json.dumps(out,indent=2),encoding='utf-8'); print(a.out)
    ''')

    write("12_SCRIPTS/rgba4_codec_reference.py", r'''
    #!/usr/bin/env python3
    """Reference codec for the RGBA4 packing proven in one completed 3DS resource.

    Packing: byte0 RRRRAAAA, byte1 BBBBGGGG. Revalidate before use elsewhere.
    """
    def decode_pixel(b0,b1):
        r=(b0>>4)&0xF; a=b0&0xF; b=(b1>>4)&0xF; g=b1&0xF
        return tuple(v*17 for v in (r,g,b,a))
    def encode_pixel(r,g,b,a):
        n=lambda v:max(0,min(15,(int(v)+8)//17))
        return bytes([(n(r)<<4)|n(a),(n(b)<<4)|n(g)])
    if __name__=='__main__':
        tests=[(0,0,0,0),(255,255,255,255),(255,0,0,255),(0,255,0,255),(0,0,255,255),(17,34,51,68)]
        for px in tests:
            raw=encode_pixel(*px); dec=decode_pixel(*raw); print(px,raw.hex(),dec)
    ''')

    write("12_SCRIPTS/build_change_manifest.py", r'''
    #!/usr/bin/env python3
    """Create changed-file manifest between original and staged trees."""
    from pathlib import Path
    import argparse,hashlib,json
    def h(p):
        x=hashlib.sha256()
        with p.open('rb') as f:
            for b in iter(lambda:f.read(1024*1024),b''): x.update(b)
        return x.hexdigest()
    def scan(r): return {p.relative_to(r).as_posix():p for p in r.rglob('*') if p.is_file()}
    ap=argparse.ArgumentParser(); ap.add_argument('original'); ap.add_argument('staged'); ap.add_argument('-o','--out',default='BUILD_CHANGE_MANIFEST.json'); a=ap.parse_args(); A=Path(a.original); B=Path(a.staged); sa=scan(A); sb=scan(B); rows=[]
    for k in sorted(set(sa)|set(sb)):
        ah=h(sa[k]) if k in sa else None; bh=h(sb[k]) if k in sb else None
        if ah!=bh: rows.append({'path':k,'before_sha256':ah,'after_sha256':bh,'status':'ADDED' if ah is None else 'REMOVED' if bh is None else 'CHANGED'})
    Path(a.out).write_text(json.dumps({'changed_count':len(rows),'files':rows},indent=2),encoding='utf-8'); print('changed=',len(rows),a.out)
    ''')

    write("12_SCRIPTS/README.md", r"""
    # Script Manifest
    - `hash_manifest.py` — deterministic file-tree SHA-256 manifest. **REUSABLE**.
    - `compare_trees.py` — path/size/hash regression comparison. **REUSABLE**.
    - `control_token_validator.py` — per-record token safety with conservative unknown handling. **REUSABLE**, regenerate policy.
    - `arabic_text_transform.py` — reference protected-token Arabic shaping/BiDi transform. **PARTIALLY REUSABLE**, renderer PoC required.
    - `visible_latin_detector.py` — review visible Latin after translation; never auto-translates identifiers. **REUSABLE**.
    - `ncsd_ncch_inventory_reference.py` — read-only container discovery helper. **PARTIALLY REUSABLE**.
    - `rgba4_codec_reference.py` — packing proven for one RGBA4 resource. **PARTIALLY REUSABLE**.
    - `build_change_manifest.py` — changed-file audit. **REUSABLE**.

    The exact historical XBB/PAPA parser/repacker and BFFNT modification scripts are not present in the final accessible repository snapshot used to build this pack. Their verified engineering requirements are documented, and the new project must use the actual format/tooling it discovers rather than a guessed reconstruction.
    """)


def build_starter():
    dirs=["config","original","extracted","translated","fonts","patches","scripts","build","output","qa","logs","docs"]
    for d in dirs: write(f"NEW_3DS_ARABIC_PROJECT/{d}/.gitkeep","")
    manifest={
        "schema_version":1,
        "project_id":"REPLACE_ME",
        "game":{"title":"","region":"","version":"","title_id":"","product_code":""},
        "source":{"filename":"","size":0,"sha256":"","read_only":True},
        "known_good":{"text_roundtrip":False,"token_safety":False,"arabic_font_poc":False,"arabic_render_poc":False,"end_to_end_runtime":False},
        "reusability":{"ah3p":"UNKNOWN","bffnt_workflow":"UNKNOWN","text_pipeline":"UNKNOWN"},
        "current_build":"",
        "frozen_components":[],
        "open_unknowns":[]
    }
    write_json("NEW_3DS_ARABIC_PROJECT/project_manifest.json",manifest)
    write_json("NEW_3DS_ARABIC_PROJECT/config/build_profile.json",{
        "source_sha256":[],"source_size":0,"build_mode":"UNKNOWN","romfs_overlay":[],"exefs_changes":[],"arabic_transform_profile":"UNPROVEN","notes":"Do not populate from the completed game without new-game evidence."
    })
    write_json("NEW_3DS_ARABIC_PROJECT/config/token_policy.json",{"movable_exact":[],"movable_prefixes":[],"strict_exact":[],"source_exceptions":[],"status":"UNPROVEN"})
    write("NEW_3DS_ARABIC_PROJECT/docs/PROJECT_CONTROL.md", (OUT/"01_SUPERVISOR/PROJECT_STATE_TEMPLATE.md").read_text(encoding="utf-8"))
    write("NEW_3DS_ARABIC_PROJECT/docs/BOOTSTRAP.md", (OUT/"16_PROJECT_BOOTSTRAP/PROJECT_BOOTSTRAP.md").read_text(encoding="utf-8"))
    write("NEW_3DS_ARABIC_PROJECT/README.md", r"""
    # New 3DS Arabic Project Starter
    Copy this directory for each new game. Keep `original/` immutable. Populate `project_manifest.json` first, then run discovery only for unknown differences. Do not copy completed-game hashes or binary assumptions into the new project.
    """)


def build_manifests():
    write("16_PROJECT_BOOTSTRAP/TOOL_SCRIPT_MANIFEST.md", (OUT/"12_SCRIPTS/README.md").read_text(encoding="utf-8"))
    write("16_PROJECT_BOOTSTRAP/FAILURE_PREVENTION_POINTER.md", "See `14_FAILURE_CASES/FAILURE_PREVENTION_GUIDE.md`.\n")
    write("16_PROJECT_BOOTSTRAP/LOCAL_EXECUTION_POINTER.md", "Copy `17_LOCAL_EXECUTION/` when a viable method is blocked by the current execution environment.\n")
    write("13_REFERENCE_FILES/REFERENCE_FILE_POLICY.md", r"""
    # Reference File Policy
    Included references are source code, manifests, hashes, workflows, and legal-safe structural notes. Full ROMs, CIA files, localized RomFS payloads, and donor game font binaries are excluded. When a binary reference is necessary, record its original path, size/hash, extraction method, and the fact that it must be supplied from a legally obtained project source.
    """)


def copy_final_sources():
    repo=ROOT.parent
    mapping={
        repo/"universal_3ds_patcher/engine.py":"13_REFERENCE_FILES/final_repo_sources/universal_3ds_patcher/engine.py",
        repo/"universal_3ds_patcher/gui.py":"13_REFERENCE_FILES/final_repo_sources/universal_3ds_patcher/gui.py",
        repo/"universal_3ds_patcher/make_patch.py":"13_REFERENCE_FILES/final_repo_sources/universal_3ds_patcher/make_patch.py",
        repo/"universal_3ds_patcher/README.txt":"13_REFERENCE_FILES/final_repo_sources/universal_3ds_patcher/README.txt",
        repo/"universal_3ds_patcher/Arabic_Hesham_3DS_Patcher.spec":"13_REFERENCE_FILES/final_repo_sources/universal_3ds_patcher/Arabic_Hesham_3DS_Patcher.spec",
        repo/"trio_installer/apply.py":"13_REFERENCE_FILES/final_repo_sources/completed_game_installer/apply.py",
        repo/"trio_installer/prepare_payload.py":"13_REFERENCE_FILES/final_repo_sources/completed_game_installer/prepare_payload.py",
        repo/"trio_installer/build_payload.py":"13_REFERENCE_FILES/final_repo_sources/completed_game_installer/build_payload.py",
        repo/"trio_installer/loc_crypto.py":"13_REFERENCE_FILES/final_repo_sources/completed_game_installer/loc_crypto.py",
        repo/".github/workflows/build-trio-installer.yml":"13_REFERENCE_FILES/final_repo_sources/workflows/build-trio-installer.yml",
        repo/".github/workflows/build-universal-3ds-patcher.yml":"13_REFERENCE_FILES/final_repo_sources/workflows/build-universal-3ds-patcher.yml",
    }
    for src,rel in mapping.items(): copy_if_exists(src,rel)
    write("13_REFERENCE_FILES/final_repo_sources/README.md", r"""
    # Final Accessible Source Snapshots
    These files are copied from the final accessible Git branch used after the completed localization. They are included as working reference implementations.

    - `universal_3ds_patcher/` demonstrates the final generic AH3P RomFS patch engine and patch builder.
    - `completed_game_installer/` demonstrates source validation, safe payload extraction, per-file verification, and output build logic from the completed game. Treat game IDs/hashes/resource assumptions as game-specific.
    - `workflows/` demonstrates moving Windows EXE builds to GitHub Actions when the interactive environment cannot build reliably.
    """)


def build_root_changelog():
    write("CHANGELOG.md", r"""
    # Changelog
    ## v1.0.0 — Knowledge transfer bootstrap
    - Converted completed-project engineering lessons into reusable role procedures, prompts, decision rules, failure-prevention guidance, scripts, local fallback template, and new-project starter tree.
    - Included final accessible generic AH3P patcher source snapshots and build workflow references.
    - Excluded copyrighted game binaries and game-specific localized payloads.
    """)


def main():
    clean()
    build_docs()
    build_scripts()
    build_starter()
    build_manifests()
    copy_final_sources()
    build_root_changelog()

    # deterministic inventory of generated pack
    rows=[]
    for p in sorted((x for x in OUT.rglob('*') if x.is_file()), key=lambda x:x.relative_to(OUT).as_posix().lower()):
        h=hashlib.sha256(p.read_bytes()).hexdigest()
        rows.append([p.relative_to(OUT).as_posix(),p.stat().st_size,h])
    write_csv("00_START_HERE/PACK_FILE_MANIFEST.csv", [["path","size","sha256"],*rows])
    print(f"created {OUT} files={len(rows)+1}")

if __name__ == '__main__':
    main()
