#!/usr/bin/env python3
"""Regenerate data/index.json from the principle records.

The manifest exists so a browser can discover each company's set without
globbing a directory. It is never hand edited: run this, and
scripts/validate.py fails if the committed manifest no longer matches the
records.
"""

import collections
import json
import os
import sys

from companies import COMPANY_META

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")



def load_records():
    by_company = collections.OrderedDict((cid, []) for cid in COMPANY_META)
    for name in sorted(os.listdir(DATA)):
        path = os.path.join(DATA, name)
        if not os.path.isdir(path) or name.startswith("."):
            continue
        if name not in COMPANY_META:
            raise SystemExit("unknown company directory data/%s" % name)
        for f in sorted(os.listdir(path)):
            if not f.endswith(".json"):
                continue
            rec = json.load(open(os.path.join(path, f)))
            by_company[name].append(rec)
    return by_company


def main():
    by_company = load_records()
    companies = []
    total = 0
    for cid, meta in COMPANY_META.items():
        records = sorted(by_company[cid], key=lambda r: r["sort"])
        total += len(records)
        companies.append(collections.OrderedDict([
            ("id", cid),
            ("name", meta["name"]),
            ("set", meta["set"]),
            ("source", meta["source"]),
            ("principles", [collections.OrderedDict([
                ("id", r["id"]),
                ("slug", r["slug"]),
                ("name", r["name"]),
                ("sort", r["sort"]),
                ("file", "data/%s/%s.json" % (cid, r["slug"])),
            ]) for r in records]),
        ]))

    index = collections.OrderedDict([
        ("version", 3),
        ("generated", "scripts/build_index.py"),
        ("companies", companies),
    ])

    path = os.path.join(DATA, "index.json")
    open(path, "w").write(json.dumps(index, indent=2, ensure_ascii=False) + "\n")
    print("wrote data/index.json with %d companies, %d principles"
          % (len(companies), total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
