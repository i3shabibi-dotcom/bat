from __future__ import annotations
import csv, hashlib, shutil, textwrap
from pathlib import Path

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'dist'/'3DS_ARABIC_LOCALIZATION_KNOWLEDGE_PACK'

def write(rel,text):
    p=OUT/rel; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(textwrap.dedent(text).lstrip('\n').rstrip()+'\n',encoding='utf-8')

write('03_BUILDER/DECISION_TREES.md', r'''
# Engineering Decision Trees

## TEXT NOT DISPLAYING
String exists in expected source resource?
- NO -> locate the real user-visible resource; do not translate an internal identifier just because it resembles text.
- YES -> continue.

String survives rebuild/re-extraction?
- NO -> extraction/reinsertion/offset/archive issue.
- YES -> continue.

Correct bytes/encoding in output?
- NO -> encoding/serializer issue.
- YES -> continue.

Required glyph exists in active font?
- NO -> font mapping/atlas issue.
- YES -> continue.

Correct resource/layer loaded at Runtime?
- UNKNOWN -> trace update/DLC/LayeredFS/build layer; do not assume precedence.
- YES -> inspect layout visibility, control tags, stale build/cache, renderer behavior.

## ARABIC BROKEN
Correct Arabic source in natural order?
-> Check builder output before Runtime.

Glyphs missing?
-> Font CMAP/atlas/mapping.

Glyphs present but disconnected?
-> shaping policy / wrong presentation forms.

Words/lines reversed?
-> BiDi policy / double-reordering / renderer native behavior.

Digits/Latin/punctuation misplaced?
-> mixed-direction handling; run dedicated mixed test set.

Only strings near tags break?
-> token sentinel/protection or control-tag placement.

## GAME CRASHES AFTER REINSERTION
Does original/no-op rebuilt archive crash?
- YES -> binary repacker/structure first.
- NO -> translation delta first.

Strict archive structure valid?
-> bounds, offsets, sizes, alignment, overlap, block sizes, string tables, reserved/unknown fields, compression.

Tokens/control sequence valid per record?
-> if no, repair translation/build transform.

Crash tied to one string/resource?
-> binary-search/minimize delta rather than rebuilding whole pipeline.

## FONT ISSUE
Missing glyph -> mapping/atlas/code point.
Wrong glyph -> CMAP/index/atlas coordinate.
Wrong spacing -> width/bearing/advance metric.
Wrong joining -> shaping, not necessarily font.
Wrong color/contrast -> pane/style/material, not necessarily font.
Only tiny text unreadable -> presentation scale/layout/raster constraint before global metric change.

## BUILD OUTPUT INCOMPLETE
Did staged payload contain file?
- NO -> payload assembly problem.
- YES -> manifest hash it.
Did overlay copy succeed?
- NO -> builder integration problem.
Did rebuilt output re-extract contain it?
- NO -> image rebuild problem.
Does output copy hash match staged file?
- NO -> rebuild/format problem.
- YES -> Runtime may be loading another resource/layer or the visible element is from another file.
''')

write('13_REFERENCE_FILES/KNOWLEDGE_PROVENANCE.md', r'''
# Knowledge Provenance and Confidence

This pack was generated from the completed project's final accessible installer/generic-patcher sources, CI build logs, recorded SHA-256 baselines, Runtime conclusions, and earlier structural/token-validation reports.

## Verified reusable facts captured
- The completed game had a byte-identical no-op text round-trip before translation and later strict structure/token gates.
- Token safety had to be enforced per record rather than by global aggregate.
- Arabic translation was authored in natural order and technical shaping/RTL was handled during build.
- Final Arabic font replacement was Runtime validated, while the donor/font binary itself is game-specific and excluded.
- Final integration required per-file output verification after rebuilding, not merely successful tool exit.
- A generic `.ah3p` RomFS overlay format and Windows patch engine were successfully built in the final accessible repository.
- Execution-environment failures were successfully bypassed using GitHub Actions rather than restarting project research.

## Explicitly not reconstructed as historical originals
The final exact historical XBB/PAPA audit/token-validator source files and BFFNT editing tool files are not present in the final accessible repository snapshot used for this package. This pack therefore transfers their proven requirements and provides generic reference implementations, but does not falsely label those reimplementations as byte-identical historical scripts.

## Game-specific items intentionally not distributed
ROM/CIA content, final localized RomFS payload, donor font binary, final BFFNT binaries, and game layout archives.
''')

write('13_REFERENCE_FILES/TECHNICAL_EXAMPLES.md', r'''
# Minimal Technical Examples

## Control code preservation
Source:
`Hello <_____MYNAME_____><PAGE><FACE_NORMAL>`

Translator-authored Arabic must preserve the exact placeholder/control spellings. The dynamic name placeholder may be moved only if policy classifies it as movable; structural controls such as page/face must retain required sequence.

## Source-relative exception principle
The completed project found source style-tag anomalies that were already unbalanced. The validator preserved those as explicit source exceptions instead of auto-inserting a guessed closing tag. Recreate this policy from the new game's untouched source.

## Arabic authoring vs build rendering
Translator field:
`arabic_natural_order = "مرحبا بالعالم"`

Builder field:
`arabic_render = <renderer-specific shaped/reordered representation>`

Do not ask translators to type visual-order Arabic.

## RGBA4 packing reference
For the proven resource:
`byte0 = RRRRAAAA`
`byte1 = BBBBGGGG`
This is a codec reference only; revalidate resource format before reuse.

## Build verification
Staged file SHA-256 == re-extracted output file SHA-256.
A successful packer return code alone is not release evidence.
''')

write('13_REFERENCE_FILES/COMPLETED_PROJECT_TOKEN_NOTES.md', r'''
# Completed-Project Token Notes — Reference Only

The completed game's text inventory contained hundreds of token spellings. Examples included player/item/character placeholders and structural tags such as PAGE/FACE/POS/font/speed/color controls. Five spellings remained intentionally classified as unknown/conservative in an early verified gate rather than guessed:
- `<ACTION_HEART_BREAK>`
- `<ACTION_RIBBON>`
- `<CANCEL_SELECT>`
- `<PARENT>`
- `<RELATIONSHIP>`

The practical lesson is reusable: unknown tokens are not an invitation to infer semantics. Preserve exact count and sequence until proven.

Two source records also contained a source-native unbalanced `<BLUE>` pattern. They were recorded as exceptions rather than normalized. New games must build their own source-exception inventory.
''')

write('13_REFERENCE_FILES/UPSTREAM_PINNING_NOTE.md', r'''
# Upstream Pinning Note

During the completed project, the Story of Seasons fan-translation repository was audited at commit:
`66e01a9f78474bbf0cdb41aeb1605725e68e90ff`

That repository was used as a tooling basis where appropriate, but its structural notes were not treated as authoritative for a different region/build when direct file inspection disagreed. This is the reusable rule: pin upstream commits, then trust the actual target files over assumptions from another region/version.
''')

# Create convenient standalone template ZIPs inside the pack.
bootstrap=OUT/'16_PROJECT_BOOTSTRAP'
local_dir=OUT/'17_LOCAL_EXECUTION'
starter=OUT/'NEW_3DS_ARABIC_PROJECT'
for zip_path, src in [
    (bootstrap/'LOCAL_EXECUTION_PACKAGE_TEMPLATE.zip', local_dir),
    (bootstrap/'NEW_PROJECT_STARTER_TEMPLATE.zip', starter),
]:
    if zip_path.exists(): zip_path.unlink()
    shutil.make_archive(str(zip_path.with_suffix('')), 'zip', root_dir=src)

# Refresh full file manifest after addenda/embedded ZIPs.
manifest=OUT/'00_START_HERE'/'PACK_FILE_MANIFEST.csv'
rows=[]
for p in sorted((x for x in OUT.rglob('*') if x.is_file() and x != manifest), key=lambda x:x.relative_to(OUT).as_posix().lower()):
    h=hashlib.sha256(p.read_bytes()).hexdigest()
    rows.append([p.relative_to(OUT).as_posix(),p.stat().st_size,h])
with manifest.open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f); w.writerow(['path','size','sha256']); w.writerows(rows)
print('addenda complete files=',len(rows)+1)
