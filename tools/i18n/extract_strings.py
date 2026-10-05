#!/usr/bin/env python3
"""Extract translatable UI strings (menu_entry .name/.help/.help2 and CHOICES(...) lists)
from Magic Lantern core src/*.c and the 200D-shipped modules.

Output: CSV with columns id,file,line,field,english,korean,status,note
id format: <relpath>:<line>:<field>[:<idx>]  (idx only for CHOICES entries)
"""
import re
import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

MODULE_DIRS = [
    "raw_video/mlv_lite", "raw_video/mlv_play", "raw_video/mlv_rec", "raw_video/mlv_snd",
    "file_man", "pic_view", "ettr", "dual_iso", "silent", "dot_tune", "autoexpo",
    "arkanoid", "deflick", "img_name", "lua", "bench", "selftest", "adv_int",
    "crop_rec", "dev_tools/edmac", "sd_uhs", "raw_video/raw_vidx", "yolo",
]

DQUOTE = chr(34)
BSLASH = chr(92) * 2  # two literal backslash chars -> regex escaped-backslash

# Matches: .name = "..."   .help = "..."   .help2 = "..."
# Field value may contain escaped quotes/backslashes.
FIELD_RE = re.compile(
    r'\.\s*(name|help|help2)\s*=\s*' + DQUOTE +
    r'((?:[^' + DQUOTE + BSLASH + r']|' + BSLASH + r'.)*)' + DQUOTE
)

STRING_LIT_RE = re.compile(
    DQUOTE + r'((?:[^' + DQUOTE + BSLASH + r']|' + BSLASH + r'.)*)' + DQUOTE
)


def find_choices_blocks(text):
    """Yield (start_line, raw_inner_text) for each CHOICES(...) occurrence, respecting paren nesting."""
    for m in re.finditer(r'\bCHOICES\s*\(', text):
        start = m.end()
        depth = 1
        i = start
        while i < len(text) and depth > 0:
            c = text[i]
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
            i += 1
        inner = text[start:i-1]
        line = text.count('\n', 0, m.start()) + 1
        yield line, inner


def extract_file(path, rows):
    rel = path.relative_to(REPO_ROOT).as_posix()
    text = path.read_text(encoding='utf-8', errors='replace')
    lines = text.split('\n')

    for lineno, line in enumerate(lines, start=1):
        for m in FIELD_RE.finditer(line):
            field, value = m.group(1), m.group(2)
            if not value.strip():
                continue
            _id = rel + ':' + str(lineno) + ':' + field
            rows.append([_id, rel, lineno, field, value, "", "untranslated", ""])

    for lineno, inner in find_choices_blocks(text):
        idx = 0
        for sm in STRING_LIT_RE.finditer(inner):
            value = sm.group(1)
            if not value.strip():
                continue
            _id = rel + ':' + str(lineno) + ':choice:' + str(idx)
            rows.append([_id, rel, lineno, 'choice:' + str(idx), value, "", "untranslated", ""])
            idx += 1


def main():
    rows = []
    src_dir = REPO_ROOT / "src"
    for c_file in sorted(src_dir.glob("*.c")):
        extract_file(c_file, rows)

    mod_root = REPO_ROOT / "modules"
    for mod in MODULE_DIRS:
        mod_dir = mod_root / mod
        if not mod_dir.is_dir():
            print("WARNING: module dir not found: " + str(mod_dir), file=sys.stderr)
            continue
        for c_file in sorted(mod_dir.glob("*.c")):
            extract_file(c_file, rows)

    out_path = REPO_ROOT / "tools" / "i18n" / "strings_ko.csv"
    with open(out_path, "w", newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(["id", "file", "line", "field", "english", "korean", "status", "note"])
        w.writerows(rows)

    print("Extracted " + str(len(rows)) + " strings -> " + str(out_path))


if __name__ == "__main__":
    main()

