#!/usr/bin/env python3
"""Fail if a held-out calibration string has leaked into data/.

The fixtures under eval/golden/ are the only calibration in this repository
written by a company rather than by us. They are worth something only for as
long as no generator has seen them. A generator that reads data/ for examples
will see anything that lands there, so the rule is mechanical: golden text
does not appear under data/.

This catches the copy and the light paraphrase. It cannot catch a generator
that was shown the fixture directly, and it cannot fingerprint a string
shorter than the shingle width -- Dawn's "Analysis paralysis" is two words
and appears in Amazon rows written years before Dawn was on the list. Those
are counted and reported rather than passed over in silence.
"""

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "eval" / "golden"
DATA = ROOT / "data"

# Long enough that ordinary shared phrasing does not trip it, short enough
# that reordering a sentence does not hide a copy.
SHINGLE = 8

WORD = re.compile(r"[a-z0-9']+")


def words(text):
    return WORD.findall(text.lower())


def shingles(text):
    w = words(text)
    return {" ".join(w[i:i + SHINGLE]) for i in range(len(w) - SHINGLE + 1)}


def golden_strings():
    """Every calibration string in every fixture, with where it came from."""
    out = []
    for path in sorted(GOLDEN.glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        company = doc["company"]["id"]
        for principle in doc["principles"]:
            for setting, text in principle["expected"].items():
                out.append((f"{company}/{principle['id']} {setting}", text))
    return out


def data_strings():
    out = []
    for path in sorted(DATA.glob("*/*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        for row in doc.get("rows", []):
            for key in ("situation", "under", "justRight", "over"):
                if key in row:
                    out.append((f"{path.relative_to(ROOT)}:{row['id']} {key}", row[key]))
    return out


def main():
    golden = golden_strings()
    if not golden:
        print("no fixtures under eval/golden/, nothing to protect", file=sys.stderr)
        return 1

    corpus = data_strings()
    corpus_shingles = [(where, shingles(text)) for where, text in corpus]

    leaks = []
    unfingerprintable = []

    for gwhere, gtext in golden:
        gshingles = shingles(gtext)
        if not gshingles:
            unfingerprintable.append((gwhere, gtext))
            continue
        for dwhere, dshingles in corpus_shingles:
            shared = gshingles & dshingles
            if shared:
                leaks.append((gwhere, dwhere, sorted(shared)[0]))

    if leaks:
        print(f"{len(leaks)} held-out string(s) present in data/:\n", file=sys.stderr)
        for gwhere, dwhere, shared in leaks:
            print(f'  {gwhere}\n    -> {dwhere}\n    shares "{shared}"', file=sys.stderr)
        print(
            "\nThe fixture is the eval. Rows in data/ are what a generator reads.\n"
            "Landing golden text in data/ makes the eval score itself.",
            file=sys.stderr,
        )
        return 1

    fixtures = len(list(GOLDEN.glob("*.json")))
    print(
        f"{len(golden)} held-out strings across {fixtures} fixture(s); "
        f"none present in {len(corpus)} strings under data/"
    )
    if unfingerprintable:
        print(
            f"{len(unfingerprintable)} shorter than {SHINGLE} words and so not checked:"
        )
        for gwhere, gtext in unfingerprintable:
            print(f"  {gwhere}: {gtext}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
