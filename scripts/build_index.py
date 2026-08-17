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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

# Catalog metadata lives here, not in the records. A record knows its
# company id. The manifest adds the public name, set title, and source.
COMPANY_META = collections.OrderedDict([
    ("amazon", {
        "name": "Amazon",
        "set": "Leadership Principles",
        "source": "https://www.amazon.jobs/content/en/our-workplace/leadership-principles",
    }),
    ("arm", {
        "name": "Arm",
        "set": "10x Mindset",
        "source": "https://careers.arm.com/life-at-arm",
    }),
    ("coupang", {
        "name": "Coupang",
        "set": "Leadership Principles",
        "source": "https://www.coupang.jobs/en/coupang-leadership-principles/",
    }),
    ("delivery-hero", {
        "name": "Delivery Hero",
        "set": "Leadership Principles",
        "source": "https://careers.deliveryhero.com/delivery-hero/2025-4/launching-our-leadership-principles",
    }),
    ("klarna", {
        "name": "Klarna",
        "set": "Leadership Principles",
        "source": "https://www.klarna.com/careers/life-at-klarna/heres-why-everyone-at-klarna-is-a-leader/",
    }),
])


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
                ("name", r["name"]),
                ("sort", r["sort"]),
                ("file", "data/%s/%s.json" % (cid, r["id"])),
            ]) for r in records]),
        ]))

    index = collections.OrderedDict([
        ("version", 2),
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
