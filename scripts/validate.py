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

from companies import COMPANY_META

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
KINDS = ("alias", "equivalent", "facet")
WORDS = ("quoted", "authored", "generated")
SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
# Sentence break for the one-to-three-sentence rule. Terminal punctuation may
# be followed by a closing quote or bracket before the space, as in
# 'is not "always." Seeks input', which is still a break. Naive about
# abbreviations on purpose: the corpus carries none, and a row that needs one
# is a row worth rewriting.
SENTENCE = re.compile(r"(?<=[.!?])[\"'\)\]]*\s+")


# Companies that publish their set under lenses, and the lens each sort
# position falls in. A company absent from this table carries no group, and
# validate_record rejects one. Arm sort 1-5 are One Arm, 6-10 are Accelerate
# Impact.
GROUP_BY_COMPANY = {
    "arm": {
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
    },
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
                with open(fpath, encoding="utf-8") as fh:
                    rec = json.load(fh)
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

    lenses = GROUP_BY_COMPANY.get(company)
    if lenses is None:
        if "group" in rec:
            errs.append("%s: %s records do not carry group, only %s do"
                        % (where, company, ", ".join(sorted(GROUP_BY_COMPANY))))
    else:
        group = rec.get("group")
        if not group:
            errs.append("%s: %s records require group" % (where, company))
        elif not SLUG.match(group):
            errs.append("%s: group %r is not kebab-case" % (where, group))
        else:
            want = lenses.get(rec.get("sort"))
            if want and group != want:
                errs.append("%s: group %r does not match sort %s (expected %s)"
                            % (where, group, rec.get("sort"), want))

    rows = rec.get("rows", [])
    # `words` is all or nothing within a record. A record with any quoted
    # calibration marks every row, so reading one file is enough to know whose
    # words each row is.
    marked = [r for r in rows if "words" in r]
    if marked and len(marked) != len(rows):
        errs.append("%s: %d of %d rows carry words, mark all of them or none"
                    % (where, len(marked), len(rows)))

    row_ids = set()
    for r in rows:
        if not SLUG.match(r.get("id", "")):
            errs.append("%s: row id %r is not kebab-case" % (where, r.get("id")))
        if r.get("id") in row_ids:
            errs.append("%s: duplicate row id %r" % (where, r.get("id")))
        row_ids.add(r.get("id"))
        for key in ("situation", "under", "justRight", "over"):
            if not r.get(key):
                errs.append("%s: row %r missing %r" % (where, r.get("id"), key))
        if "words" in r and r["words"] not in WORDS:
            errs.append("%s: row %r has words %r, expected one of %s"
                        % (where, r.get("id"), r.get("words"), ", ".join(WORDS)))
        # Quoted calibration is the company's writing, so the sentence rule
        # does not apply to it, the same way it does not apply to definition.
        # The situation label is ours either way.
        if r.get("words") == "quoted":
            continue
        for key in ("under", "justRight", "over"):
            text = (r.get(key) or "").strip()
            if not text:
                continue
            n = len([x for x in SENTENCE.split(text) if x])
            if not 1 <= n <= 3:
                errs.append("%s: row %r %s has %d sentences, expected one to three"
                            % (where, r.get("id"), key, n))
    if not 5 <= len(rows) <= 12:
        errs.append("%s: has %d rows, expected five to 12" % (where, len(rows)))

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
            with open(index_path, encoding="utf-8") as fh:
                index = json.load(fh)
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
    whose = collections.Counter()
    kinds = {}
    for items in by_company.values():
        for _, rec in items:
            n_rows += len(rec["rows"])
            for r in rec["rows"]:
                whose[r.get("words", "authored")] += 1
            for t in rec["terms"]:
                kinds[t["kind"]] = kinds.get(t["kind"], 0) + 1
    print("OK: %d companies, %d principles, %d rows, %d terms (%s)"
          % (len(by_company),
             n_principles,
             n_rows,
             sum(kinds.values()),
             ", ".join("%s %d" % kv for kv in sorted(kinds.items()))))
    print("rows by whose words: %s"
          % ", ".join("%s %d" % (k, whose[k]) for k in WORDS if whose[k]))

    # Not an error. An id is unique within a company and nowhere else, so a
    # consumer keys on (company, id). Printing the collisions keeps that
    # visible here rather than discovered in an app.
    shared = collections.defaultdict(list)
    for company, items in by_company.items():
        for _, rec in items:
            shared[rec.get("id")].append(company)
    shared = {k: v for k, v in shared.items() if len(v) > 1}
    if shared:
        print("ids used by more than one company, address by (company, id):")
        for pid in sorted(shared):
            print("  %-28s %s" % (pid, ", ".join(sorted(shared[pid]))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
