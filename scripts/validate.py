#!/usr/bin/env python3
"""Validate the principle records. Exits non-zero on any problem.

Checks the invariants SCHEMA.md states, so the rules are enforced by this
script rather than by a human remembering to read the document.
"""

import collections
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
KINDS = ("alias", "equivalent", "facet")
SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

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

# Arm lenses. sort 1-5 are One Arm, sort 6-10 are Accelerate Impact.
ARM_GROUP_BY_SORT = {
    1: "one-arm",
    2: "one-arm",
    3: "one-arm",
    4: "one-arm",
    5: "one-arm",
    6: "accelerate-impact",
    7: "accelerate-impact",
    8: "accelerate-impact",
    9: "accelerate-impact",
    10: "accelerate-impact",
}


def slug(s):
    s = s.lower().replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def check_style(obj, where, errs):
    if isinstance(obj, dict):
        for v in obj.values():
            check_style(v, where, errs)
    elif isinstance(obj, list):
        for v in obj:
            check_style(v, where, errs)
    elif isinstance(obj, str):
        if "\u2014" in obj or "\u2013" in obj:
            errs.append("%s: em dash or en dash in %r" % (where, obj[:80]))
        if "---" in obj:
            errs.append("%s: --- in %r" % (where, obj[:80]))


def load_records(errs):
    by_company = collections.OrderedDict((cid, []) for cid in COMPANY_META)

    for name in sorted(os.listdir(DATA)):
        path = os.path.join(DATA, name)
        if name.startswith("."):
            continue
        if os.path.isfile(path):
            if name != "index.json":
                errs.append("data/%s: only index.json may sit directly under data/"
                            % name)
            continue
        if not os.path.isdir(path):
            continue
        if name not in COMPANY_META:
            errs.append("data/%s: unknown company directory" % name)
            continue
        for f in sorted(os.listdir(path)):
            fpath = os.path.join(path, f)
            if os.path.isdir(fpath):
                errs.append("data/%s/%s: unexpected directory" % (name, f))
                continue
            if not f.endswith(".json"):
                errs.append("data/%s/%s: only .json records belong here"
                            % (name, f))
                continue
            try:
                rec = json.load(open(fpath))
            except ValueError as e:
                errs.append("data/%s/%s: not valid JSON, %s" % (name, f, e))
                continue
            by_company[name].append((f, rec))
    return by_company


def validate_record(company, filename, rec, errs):
    where = "%s/%s" % (company, rec.get("id", filename))
    stem = filename[:-5] if filename.endswith(".json") else filename

    if rec.get("id") != stem:
        errs.append("%s: id %r does not match the filename" % (where, rec.get("id")))
    if rec.get("company") != company:
        errs.append("%s: company %r does not match the directory"
                    % (where, rec.get("company")))

    required = ("id", "company", "name", "sort", "definition", "terms", "rows")
    for key in required:
        if key not in rec:
            errs.append("%s: missing %r" % (where, key))
    if not SLUG.match(rec.get("id", "")):
        errs.append("%s: id is not kebab-case" % where)
    if not SLUG.match(rec.get("company", "")):
        errs.append("%s: company is not kebab-case" % where)

    if company == "amazon":
        if "group" in rec:
            errs.append("%s: Amazon records do not carry group" % where)
    elif company == "arm":
        group = rec.get("group")
        if not group:
            errs.append("%s: Arm records require group" % where)
        elif not SLUG.match(group):
            errs.append("%s: group %r is not kebab-case" % (where, group))
        else:
            want = ARM_GROUP_BY_SORT.get(rec.get("sort"))
            if want and group != want:
                errs.append("%s: group %r does not match sort %s (expected %s)"
                            % (where, group, rec.get("sort"), want))
    elif "group" in rec and rec.get("group") and not SLUG.match(rec.get("group", "")):
        errs.append("%s: group %r is not kebab-case" % (where, rec.get("group")))

    row_ids = set()
    for r in rec.get("rows", []):
        if not SLUG.match(r.get("id", "")):
            errs.append("%s: row id %r is not kebab-case" % (where, r.get("id")))
        if r.get("id") in row_ids:
            errs.append("%s: duplicate row id %r" % (where, r.get("id")))
        row_ids.add(r.get("id"))
        for key in ("situation", "under", "justRight", "over"):
            if not r.get(key):
                errs.append("%s: row %r missing %r" % (where, r.get("id"), key))
    if not 5 <= len(rec.get("rows", [])) <= 12:
        errs.append("%s: has %d rows, expected five to 12"
                    % (where, len(rec.get("rows", []))))

    local = set()
    for t in rec.get("terms", []):
        tid = t.get("id", "")
        if not SLUG.match(tid):
            errs.append("%s: term id %r is not kebab-case" % (where, tid))
        if slug(t.get("label", "")) != tid:
            errs.append("%s: term id %r is not the slug of label %r"
                        % (where, tid, t.get("label")))
        if tid in local:
            errs.append("%s: duplicate term id %r" % (where, tid))
        local.add(tid)
        if t.get("kind") not in KINDS:
            errs.append("%s: term %r has kind %r, expected one of %s"
                        % (where, tid, t.get("kind"), ", ".join(KINDS)))
        if t.get("kind") == "facet":
            if not t.get("rows"):
                errs.append("%s: facet %r carries no rows" % (where, tid))
            for rid in t.get("rows", []):
                if rid not in row_ids:
                    errs.append("%s: facet %r points at unknown row %r"
                                % (where, tid, rid))
        elif "rows" in t:
            errs.append("%s: term %r is %s but carries rows"
                        % (where, tid, t.get("kind")))

    check_style(rec, where, errs)
    return row_ids


def expected_index(by_company):
    companies = []
    for cid, meta in COMPANY_META.items():
        records = [rec for _, rec in by_company[cid]]
        records.sort(key=lambda r: r.get("sort", 0))
        companies.append({
            "id": cid,
            "name": meta["name"],
            "set": meta["set"],
            "source": meta["source"],
            "principles": [
                {"id": r["id"], "name": r["name"], "sort": r["sort"],
                 "file": "data/%s/%s.json" % (cid, r["id"])}
                for r in records
            ],
        })
    return {
        "version": 2,
        "generated": "scripts/build_index.py",
        "companies": companies,
    }


def main():
    errs = []
    by_company = load_records(errs)

    for company, items in by_company.items():
        for filename, rec in items:
            validate_record(company, filename, rec, errs)

        # sort is unique 1..n per company
        sorts = [rec.get("sort") for _, rec in items]
        if sorted(sorts) != list(range(1, len(items) + 1)):
            errs.append("%s: sort must be one through %d with no gaps or repeats, got %s"
                        % (company, len(items), sorted(sorts)))

        # term ids unique per company
        seen = {}
        for _, rec in items:
            for t in rec.get("terms", []):
                tid = t.get("id")
                if tid in seen:
                    errs.append("%s: term id %r used by both %s and %s"
                                % (company, tid, seen[tid], rec.get("id")))
                seen[tid] = rec.get("id")

    index_path = os.path.join(DATA, "index.json")
    if not os.path.exists(index_path):
        errs.append("data/index.json is missing")
    else:
        try:
            index = json.load(open(index_path))
        except ValueError as e:
            errs.append("data/index.json: not valid JSON, %s" % e)
            index = None
        if index is not None:
            if index.get("version") != 2:
                errs.append("data/index.json: version must be 2, got %r"
                            % index.get("version"))
            want = expected_index(by_company)
            # Compare the generated shape, ignoring key order by using the
            # same structure validate just built from the records.
            if (index.get("generated") != want["generated"]
                    or index.get("companies") != want["companies"]):
                errs.append("data/index.json is stale, rebuild it")
            check_style(index, "data/index.json", errs)

    if errs:
        print("FAIL (%d)" % len(errs))
        for e in errs:
            print("  " + e)
        return 1

    n_principles = sum(len(items) for items in by_company.values())
    n_rows = 0
    kinds = {}
    for items in by_company.values():
        for _, rec in items:
            n_rows += len(rec["rows"])
            for t in rec["terms"]:
                kinds[t["kind"]] = kinds.get(t["kind"], 0) + 1
    print("OK: %d companies, %d principles, %d rows, %d terms (%s)"
          % (len(by_company),
             n_principles,
             n_rows,
             sum(kinds.values()),
             ", ".join("%s %d" % kv for kv in sorted(kinds.items()))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
