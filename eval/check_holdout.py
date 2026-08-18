#!/usr/bin/env python3
"""Guard the held-out calibration in eval/golden/.

The fixtures here are the only calibration in this repository written by a
company rather than by us. They are worth something only for as long as no
generator has been shown them.

Two things are checked.

**No leak.** Golden text must not appear in an authored row. A generator that
reads this corpus for examples sees every authored row, so golden text landing
in one puts the eval inside the model's input. Compared on eight-word shingles,
which catches the copy and the light paraphrase.

**No drift.** A row marked `words: "quoted"` is a transcription of the company,
so where a fixture covers the same principle the two must agree exactly. A
mismatch means a quotation was edited, or one of the two transcriptions is
wrong.

Rows marked `quoted` are deliberately exempt from the leak check. That is the
point of the marker: the company's own calibration can live in `data/` where
people can read it, because a generator can and must skip it. See SCHEMA.md.

Neither check can see a prompt. Paste a fixture into a generator as few-shot
examples and nothing here will notice.
"""

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "eval" / "golden"
DATA = ROOT / "data"

SETTINGS = ("under", "justRight", "over")

# Long enough that ordinary shared phrasing does not trip it, short enough that
# reordering a sentence does not hide a copy. Golden strings shorter than this
# cannot be fingerprinted and are reported by name instead.
SHINGLE = 8

WORD = re.compile(r"[a-z0-9']+")


def words(text):
    return WORD.findall(text.lower())


def shingles(text):
    w = words(text)
    return {" ".join(w[i:i + SHINGLE]) for i in range(len(w) - SHINGLE + 1)}


def load_golden():
    """{company: {principle id: {setting: text}}}, plus a flat list."""
    by_company = {}
    flat = []
    for path in sorted(GOLDEN.glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        company = doc["company"]["id"]
        principles = by_company.setdefault(company, {})
        for p in doc["principles"]:
            principles[p["id"]] = p["expected"]
            for setting, text in p["expected"].items():
                flat.append((f"{company}/{p['id']} {setting}", text))
    return by_company, flat


def load_rows():
    for path in sorted(DATA.glob("*/*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        for row in doc.get("rows", []):
            yield path.relative_to(ROOT), doc, row


def main():
    golden_by_company, golden = load_golden()
    if not golden:
        print("no fixtures under eval/golden/, nothing to protect", file=sys.stderr)
        return 1

    authored = []
    quoted = []
    for path, doc, row in load_rows():
        where = f"{path}:{row['id']}"
        target = quoted if row.get("words") == "quoted" else authored
        target.append((where, doc, row))

    errs = []

    # No leak.
    corpus = [
        (f"{where} {key}", shingles(row[key]))
        for where, _, row in authored
        for key in SETTINGS
        if row.get(key)
    ]
    unfingerprintable = []
    for gwhere, gtext in golden:
        gshingles = shingles(gtext)
        if not gshingles:
            unfingerprintable.append((gwhere, gtext))
            continue
        for dwhere, dshingles in corpus:
            shared = gshingles & dshingles
            if shared:
                errs.append(
                    f'leak: {gwhere}\n    -> authored row {dwhere}\n'
                    f'    shares "{sorted(shared)[0]}"'
                )

    # No drift.
    checked = 0
    for where, doc, row in quoted:
        expected = golden_by_company.get(doc["company"], {}).get(doc["id"])
        if expected is None:
            continue
        checked += 1
        for key in SETTINGS:
            if row.get(key) != expected[key]:
                errs.append(
                    f"drift: {where} {key} does not match the fixture\n"
                    f"    fixture: {expected[key][:90]}\n"
                    f"    record:  {(row.get(key) or '')[:90]}"
                )

    if errs:
        print(f"{len(errs)} problem(s):\n", file=sys.stderr)
        for e in errs:
            print("  " + e, file=sys.stderr)
        print(
            "\nThe fixture is the eval. Authored rows are what a generator reads\n"
            "and what it is scored against. Golden text in an authored row makes\n"
            "the eval score itself.",
            file=sys.stderr,
        )
        return 1

    fixtures = len(list(GOLDEN.glob("*.json")))
    print(
        f"{len(golden)} held-out strings across {fixtures} fixture(s); "
        f"none present in {len(corpus)} authored strings under data/"
    )
    print(f"{len(quoted)} quoted rows under data/, {checked} covered by a fixture and matching")
    if unfingerprintable:
        print(f"{len(unfingerprintable)} shorter than {SHINGLE} words and so not checked:")
        for gwhere, gtext in unfingerprintable:
            print(f"  {gwhere}: {gtext}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
