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
# Numbers per company block. Generous on purpose: the largest set here is
# 15, and a company that outgrows a thousand principles has a bigger
# problem than this file.
BLOCK_SIZE = 1000
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
# Impact. Toyota sort 1-3 are Continuous Improvement, 4-5 are Respect for
# People. Dawn's seven headings are from its September 2024 poster and do not
# follow the numbering, so the table is the only place the mapping lives.
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
    "toyota": {
        1: "continuous-improvement",
        2: "continuous-improvement",
        3: "continuous-improvement",
        4: "respect-for-people",
        5: "respect-for-people",
    },
    "dawn": {
        1: "strategic-approach",
        2: "customer-focus",
        3: "collaboration-and-communication",
        4: "ownership-and-accountability",
        5: "ownership-and-accountability",
        6: "innovation-and-continuous-improvement",
        7: "agility-and-action",
        8: "collaboration-and-communication",
        9: "innovation-and-continuous-improvement",
        10: "talent-and-development",
        11: "agility-and-action",
        12: "ownership-and-accountability",
        13: "innovation-and-continuous-improvement",
        14: "strategic-approach",
        15: "strategic-approach",
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
            if name not in ("index.json", "facets.json"):
                errs.append("data/%s: only index.json and facets.json may sit directly under data/"
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
    where = "%s/%s" % (company, rec.get("slug", filename))
    stem = filename[:-5] if filename.endswith(".json") else filename

    if rec.get("slug") != stem:
        errs.append("%s: slug %r does not match the filename"
                    % (where, rec.get("slug")))
    if rec.get("company") != company:
        errs.append("%s: company %r does not match the directory"
                    % (where, rec.get("company")))

    required = ("id", "slug", "company", "name", "sort", "definition",
                "terms", "rows")
    for key in required:
        if key not in rec:
            errs.append("%s: missing %r" % (where, key))

    # The id is a number so that it can be globally unique, which is what
    # stops an app that looks a principle up by id alone from landing on
    # another company's record. The block says which company owns it.
    pid = rec.get("id")
    block = COMPANY_META.get(company, {}).get("block")
    if not isinstance(pid, int) or isinstance(pid, bool):
        errs.append("%s: id %r is not a number" % (where, pid))
    elif block is not None and not block < pid < block + BLOCK_SIZE:
        errs.append("%s: id %d is outside %s's block, %d to %d"
                    % (where, pid, company, block + 1, block + BLOCK_SIZE - 1))

    if not SLUG.match(rec.get("slug") or ""):
        errs.append("%s: slug is not kebab-case" % where)
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
    # One row, at least. A principle that decomposes into no observable
    # behavior is not modeled, and that is the schema's one real claim. How
    # many rows past one is editorial and belongs in review: a company that
    # published a single triple gets one, and a principle that earns 15
    # situations gets 15.
    if not rows:
        errs.append("%s: has no rows, so nothing about it is observable" % where)

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


def is_inline_generated(row):
    """True when the facet row carries its own prose instead of a record ref."""
    if not isinstance(row, dict):
        return False
    return any(k in row for k in ("situation", "under", "justRight", "over"))


def validate_generated_row(row, where, errs):
    """An inline facet row belongs to the facet, not to a company record."""
    rid = row.get("id")
    label = "%s generated row %r" % (where, rid)
    if "principle" in row:
        errs.append("%s: must not name a principle" % label)
    if row.get("words") != "generated":
        errs.append("%s: words must be generated, got %r" % (label, row.get("words")))
    for key in ("situation", "under", "justRight", "over"):
        if not row.get(key):
            errs.append("%s: missing %r" % (label, key))
    for key in ("under", "justRight", "over"):
        text = (row.get(key) or "").strip()
        if not text:
            continue
        n = len([x for x in SENTENCE.split(text) if x])
        if not 1 <= n <= 3:
            errs.append("%s: %s has %d sentences, expected one to three"
                        % (label, key, n))


def load_facets(errs):
    """Load data/facets.json if it exists, validating its basic structure."""
    path = os.path.join(DATA, "facets.json")
    if not os.path.exists(path):
        errs.append("data/facets.json is missing")
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            facets = json.load(fh)
    except ValueError as e:
        errs.append("data/facets.json: not valid JSON, %s" % e)
        return None
    return facets


def validate_facets(facets, principle_rows, errs):
    """Validate facets.json against the principle records.

    principle_rows is a dict mapping principle id to the set of row ids on
    that principle.
    """
    if facets is None:
        return {}

    if facets.get("version") != 1:
        errs.append("data/facets.json: version must be 1, got %r"
                    % facets.get("version"))

    if not isinstance(facets.get("facets"), list):
        errs.append("data/facets.json: facets must be an array")
        return {}

    seen_ids = set()
    principle_to_facets = collections.defaultdict(list)

    for f in facets.get("facets", []):
        fid = f.get("id", "")
        where = "data/facets.json facet %r" % fid

        if not SLUG.match(fid):
            errs.append("%s: id is not kebab-case" % where)
        if fid in seen_ids:
            errs.append("%s: duplicate facet id" % where)
        seen_ids.add(fid)

        label = f.get("label", "")
        if not label:
            errs.append("%s: missing label" % where)
        elif slug(label) != fid:
            errs.append("%s: id %r is not the slug of label %r"
                        % (where, fid, label))

        principles = f.get("principles", [])
        if not principles:
            errs.append("%s: must list at least one principle" % where)
        for pid in principles:
            if not isinstance(pid, int) or isinstance(pid, bool):
                errs.append("%s: principle %r is not a number" % (where, pid))
            elif pid not in principle_rows:
                errs.append("%s: principle %d does not exist" % (where, pid))
            else:
                principle_to_facets[pid].append(fid)

        listed = set(p for p in principles
                     if isinstance(p, int) and not isinstance(p, bool))

        rows = f.get("rows", [])
        if not rows:
            errs.append("%s: must list at least one row" % where)
        row_ids = set()
        n_source = 0
        for row in rows:
            rid = row.get("id")
            if not SLUG.match(rid or ""):
                errs.append("%s: row id %r is not kebab-case" % (where, rid))
            elif rid in row_ids:
                errs.append("%s: duplicate row id %r" % (where, rid))
            else:
                row_ids.add(rid)
            if is_inline_generated(row):
                validate_generated_row(row, where, errs)
                continue
            n_source += 1
            rpid = row.get("principle")
            if not isinstance(rpid, int) or isinstance(rpid, bool):
                errs.append("%s: row principle %r is not a number" % (where, rpid))
                continue
            if rpid not in principle_rows:
                errs.append("%s: row references principle %d which does not exist"
                            % (where, rpid))
            elif rid not in principle_rows[rpid]:
                errs.append("%s: row references %d/%r which does not exist"
                            % (where, rpid, rid))
            # A row from a principle the facet does not list would render on
            # every member of the facet while its own principle never gets
            # the facet in the index.
            if rpid not in listed:
                errs.append("%s: row principle %d is not in this facet's principles"
                            % (where, rpid))

        if rows and n_source == 0:
            errs.append("%s: must list at least one source ref" % where)

        check_style(f, where, errs)

    return principle_to_facets


def validate_company(company, items, errs):
    """Checks that span one company's directory rather than one record."""
    # sort is unique 1..n per company. A record whose sort is missing or not
    # a number has already been reported by validate_record; it must not
    # crash this comparison, or the queued errors never print.
    numeric = sorted(rec.get("sort") for _, rec in items
                     if isinstance(rec.get("sort"), int)
                     and not isinstance(rec.get("sort"), bool))
    if numeric != list(range(1, len(items) + 1)):
        errs.append("%s: sort must be one through %d with no gaps or repeats, got %s"
                    % (company, len(items), numeric))

    # term ids unique per company
    seen = {}
    for _, rec in items:
        for t in rec.get("terms", []):
            tid = t.get("id")
            if tid in seen:
                errs.append("%s: term id %r used by both %s and %s"
                            % (company, tid, seen[tid], rec.get("id")))
            seen[tid] = rec.get("id")


def expected_index(by_company, principle_to_facets):
    companies = []
    for cid, meta in COMPANY_META.items():
        # A record missing one of these keys has already failed validation;
        # skipping it here keeps the run alive so those errors print instead
        # of a KeyError traceback. The comparison against index.json may then
        # also report the index as stale, which is true until the record is
        # fixed and the index rebuilt.
        records = [rec for _, rec in by_company[cid]
                   if all(k in rec for k in ("id", "slug", "name", "sort"))
                   and isinstance(rec.get("sort"), int)
                   and not isinstance(rec.get("sort"), bool)]
        records.sort(key=lambda r: r["sort"])
        principles = []
        for r in records:
            pid = r["id"]
            facet_ids = sorted(principle_to_facets.get(pid, []))
            p = {"id": pid, "slug": r["slug"], "name": r["name"],
                 "sort": r["sort"],
                 "file": "data/%s/%s.json" % (cid, r["slug"])}
            if facet_ids:
                p["facets"] = facet_ids
            principles.append(p)
        companies.append({
            "id": cid,
            "name": meta["name"],
            "set": meta["set"],
            "source": meta["source"],
            "principles": principles,
        })
    return {
        "version": 5,
        "generated": "scripts/build_index.py",
        "companies": companies,
    }


def main():
    errs = []
    by_company = load_records(errs)

    # Build principle_rows: principle id -> set of row ids
    principle_rows = {}
    for company, items in by_company.items():
        for filename, rec in items:
            row_ids = validate_record(company, filename, rec, errs)
            pid = rec.get("id")
            if isinstance(pid, int) and not isinstance(pid, bool):
                principle_rows[pid] = row_ids

        validate_company(company, items, errs)

    # Globally unique ids. This is the property the whole scheme exists for,
    # so it is checked across the corpus rather than per company.
    seen_ids = {}
    for company, items in by_company.items():
        for _, rec in items:
            pid = rec.get("id")
            if not isinstance(pid, int) or isinstance(pid, bool):
                continue
            if pid in seen_ids:
                errs.append("id %d used by both %s and %s"
                            % (pid, seen_ids[pid], "%s/%s" % (company, rec.get("slug"))))
            seen_ids[pid] = "%s/%s" % (company, rec.get("slug"))

    # Validate facets.json
    facets = load_facets(errs)
    principle_to_facets = validate_facets(facets, principle_rows, errs)

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
            if index.get("version") != 5:
                errs.append("data/index.json: version must be 5, got %r"
                            % index.get("version"))
            want = expected_index(by_company, principle_to_facets)
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
    n_facets = len(facets.get("facets", [])) if facets else 0
    n_mapped = len(principle_to_facets)
    print("OK: %d companies, %d principles, %d rows, %d terms (%s), %d facets (%d principles mapped)"
          % (len(by_company),
             n_principles,
             n_rows,
             sum(kinds.values()),
             ", ".join("%s %d" % kv for kv in sorted(kinds.items())),
             n_facets,
             n_mapped))
    print("rows by whose words: %s"
          % ", ".join("%s %d" % (k, whose[k]) for k in WORDS if whose[k]))

    # Not an error. A slug is unique within a company and nowhere else, which
    # is fine now that the id carries identity. Two companies sharing a slug
    # is the signal that they may be describing the same behavior, so it is
    # worth seeing rather than hiding.
    shared = collections.defaultdict(list)
    for company, items in by_company.items():
        for _, rec in items:
            shared[rec.get("slug")].append(company)
    shared = {k: v for k, v in shared.items() if len(v) > 1}
    if shared:
        print("slugs used by more than one company, which is allowed:")
        for slug_ in sorted(shared):
            print("  %-34s %s" % (slug_, ", ".join(sorted(shared[slug_]))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
