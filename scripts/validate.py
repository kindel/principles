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

import essay_links
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
LP_TOKEN = re.compile(r"\{lp:([a-z0-9]+(?:-[a-z0-9]+)*)\}")
TEACH_PROSE = ("why", "calibrationIntro", "examples", "looksLike", "deepen")
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


def check_teaching_dashes(obj, where, errs, path=""):
    """Reject an em dash or ---. An en dash is allowed only in a blog title.

    A published Further reading title keeps the source heading's
    punctuation. One title in this corpus uses an en dash (U+2013).
    Authored prose does not get that exception. check_style rejects every
    en dash, which is right for principle records and wrong for these
    titles, so teaching files do not call it.
    """
    if isinstance(obj, dict):
        for k, v in obj.items():
            check_teaching_dashes(v, where, errs, path + "." + str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            check_teaching_dashes(v, where, errs, "%s[%d]" % (path, i))
    elif isinstance(obj, str):
        published_title = path.endswith(".title") and ".blog[" in path
        if "\u2014" in obj or ("\u2013" in obj and not published_title):
            errs.append("%s: em dash or en dash in %r" % (where, obj[:80]))
        if "---" in obj:
            errs.append("%s: --- in %r" % (where, obj[:80]))


def _nonempty_str(value):
    return isinstance(value, str) and bool(value.strip())


def take_preamble(cid, meta, errs):
    """The opening paragraph, or None when the company has none.

    A present value that is not a non-empty string is an error. Callers
    omit the key rather than copy the bad value into the manifest.
    """
    if "preamble" not in meta:
        return None
    value = meta["preamble"]
    if not _nonempty_str(value):
        errs.append("%s: preamble must be a non-empty string" % cid)
        return None
    return value


def validate_blog(items, where, errs):
    """Further reading is a non-empty list of title, url, and note."""
    if not isinstance(items, list) or not items:
        errs.append("%s: blog must be a non-empty list" % where)
        return
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            errs.append("%s: blog[%d] must be an object" % (where, i))
            continue
        for key in ("title", "url", "note"):
            if not _nonempty_str(item.get(key)):
                errs.append("%s: blog[%d].%s must be a non-empty string"
                            % (where, i, key))


def validate_teaching_shape(doc, where, errs):
    """The counts and object shapes SCHEMA.md states for one principle."""
    why = doc.get("why")
    if (not isinstance(why, list) or not 3 <= len(why) <= 6
            or not all(_nonempty_str(x) for x in why)):
        errs.append("%s: why must be 3 to 6 paragraphs" % where)
    intro = doc.get("calibrationIntro")
    if not _nonempty_str(intro):
        errs.append("%s: calibrationIntro must be a non-empty string" % where)
    examples = doc.get("examples")
    if not isinstance(examples, list) or not 2 <= len(examples) <= 4:
        errs.append("%s: examples must be 2 to 4 cases" % where)
    else:
        for i, item in enumerate(examples):
            if (not isinstance(item, dict) or not _nonempty_str(item.get("title"))
                    or not _nonempty_str(item.get("body"))):
                errs.append("%s: examples[%d] needs a title and a body" % (where, i))
    looks = doc.get("looksLike")
    if (not isinstance(looks, dict)
            or not _nonempty_str(looks.get("individual"))
            or not _nonempty_str(looks.get("manager"))):
        errs.append("%s: looksLike needs individual and manager" % where)
    deepen = doc.get("deepen")
    if (not isinstance(deepen, list) or not 6 <= len(deepen) <= 12
            or not all(_nonempty_str(x) for x in deepen)):
        errs.append("%s: deepen must be 6 to 12 questions" % where)
    elif any(not x.endswith("?") for x in deepen):
        errs.append("%s: each deepen question must end with ?" % where)
    related = doc.get("related")
    if not isinstance(related, list) or len(related) < 2:
        errs.append("%s: related needs at least two principles" % where)


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
        if name in ("teaching", "maps"):
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
    # A principle with no rows is not modeled. The one exception is a company
    # marked calibration "unpublished": the definitions are published and the
    # calibration is not. Inventing rows to clear the flag is not allowed.
    unpublished = COMPANY_META.get(company, {}).get("calibration") == "unpublished"
    if not rows and not unpublished:
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
        # A source ref is scoped by its principle. Row ids are unique within
        # a principle, not across the facet, and two principles on one facet
        # may name the same situation (Coupang 3007 mirrors Amazon 1013).
        # Inline generated rows are one app table, so their ids stand alone,
        # and they never reuse a source ref's id: the generator reserves
        # those, so a shadowed ref id here is hand-edited ambiguity.
        seen_rows = set()
        ref_ids = set()
        inline_ids = set()
        n_source = 0
        for row in rows:
            rid = row.get("id")
            inline = is_inline_generated(row)
            key = (None, rid) if inline else (row.get("principle"), rid)
            if not SLUG.match(rid or ""):
                errs.append("%s: row id %r is not kebab-case" % (where, rid))
            elif key in seen_rows:
                if inline:
                    errs.append("%s: duplicate row id %r" % (where, rid))
                else:
                    errs.append("%s: duplicate row ref %r/%r"
                                % (where, row.get("principle"), rid))
            elif inline and rid in ref_ids:
                errs.append("%s: generated row id %r reuses a source ref id"
                            % (where, rid))
            elif not inline and rid in inline_ids:
                errs.append("%s: row ref %r/%r reuses a generated row id"
                            % (where, row.get("principle"), rid))
            else:
                seen_rows.add(key)
                (inline_ids if inline else ref_ids).add(rid)
            if inline:
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

        # A source ref points at human rows. A principle with no record rows
        # (unpublished calibration) has nothing to point at. A facet whose
        # every known member is in that state may be generated rows only.
        # A member that has record rows still requires a source ref.
        known = [pid for pid in listed if pid in principle_rows]
        members_with_rows = [pid for pid in known if principle_rows[pid]]
        if rows and n_source == 0 and (not known or members_with_rows):
            errs.append("%s: must list at least one source ref" % where)

        check_style(f, where, errs)

    return principle_to_facets


def validate_calibration_coverage(facets, principle_rows, principle_to_facets, names, errs):
    """Every principle must have generated calibration rows.

    Porridge's table is those rows. A principle with none is an empty page,
    not an unpublished draft. Record rows may still be empty when the company
    marks calibration unpublished. That flag does not excuse a missing table.
    """
    if not facets:
        return
    generated = set()
    for f in facets.get("facets", []):
        fid = f.get("id")
        rows = f.get("rows") or []
        if any(isinstance(row, dict) and is_inline_generated(row)
               and row.get("words") == "generated" and row.get("under")
               for row in rows):
            generated.add(fid)
    for pid in sorted(principle_rows):
        label = names.get(pid, str(pid))
        facs = principle_to_facets.get(pid) or []
        if not facs:
            errs.append("%s has no calibration table" % label)
        elif not any(fid in generated for fid in facs):
            errs.append("%s has no calibration table (on %s, which has no generated rows)"
                        % (label, ", ".join(facs)))


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


def expected_index(by_company, principle_to_facets, errs=None):
    if errs is None:
        errs = []
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
        company = {
            "id": cid,
            "name": meta["name"],
            "set": meta["set"],
            "source": meta["source"],
        }
        preamble = take_preamble(cid, meta, errs)
        if preamble is not None:
            company["preamble"] = preamble
        company["principles"] = principles
        companies.append(company)
    return {
        "version": 5,
        "generated": "scripts/build_index.py",
        "companies": companies,
    }


def _strings(obj, out):
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            _strings(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _strings(v, out)


def validate_teaching(by_company, errs, root=None):
    """Teaching files point at real principles.

    A slug in data/teaching/<company>/ must be a principle of that company.
    Each related id must be one too. Every {lp:slug} token in the prose
    must resolve, and it must be listed in related. A token in the catalog
    must resolve. root is for tests; the corpus uses DATA.
    """
    catalog, catalog_err = essay_links.load_catalog()
    if catalog_err:
        errs.append("scripts/essay_catalog.json: %s" % catalog_err)
        catalog = None
    teaching = os.path.join(root or DATA, "teaching")
    if not os.path.isdir(teaching):
        return
    for company in sorted(os.listdir(teaching)):
        cdir = os.path.join(teaching, company)
        if company.startswith("."):
            continue
        if not os.path.isdir(cdir):
            errs.append("data/teaching/%s: not a directory" % company)
            continue
        if company not in by_company:
            errs.append("data/teaching/%s: unknown company" % company)
            continue
        slugs = {}
        for _, rec in by_company[company]:
            slug_ = rec.get("slug")
            if isinstance(slug_, str):
                slugs[slug_] = rec
        for filename in sorted(os.listdir(cdir)):
            path = os.path.join(cdir, filename)
            where = "data/teaching/%s/%s" % (company, filename)
            if not filename.endswith(".json") or not os.path.isfile(path):
                errs.append("%s: only .json teaching files belong here" % where)
                continue
            try:
                with open(path, encoding="utf-8") as fh:
                    doc = json.load(fh)
            except ValueError as e:
                errs.append("%s: not valid JSON, %s" % (where, e))
                continue
            if not isinstance(doc, dict):
                errs.append("%s: must be a JSON object" % where)
                continue
            if catalog is not None:
                essay_links.check_value(doc, where, catalog, errs)
            check_teaching_dashes(doc, where, errs)
            if filename == "index.json":
                principles = doc.get("principles")
                if not isinstance(principles, list) or not principles:
                    errs.append("%s: principles must be a non-empty list" % where)
                else:
                    for item in principles:
                        if not isinstance(item, dict):
                            errs.append("%s: catalog entry must be an object" % where)
                            continue
                        slug_ = item.get("slug")
                        if slug_ not in slugs:
                            errs.append("%s: catalog slug %r does not exist" % (where, slug_))
                            continue
                        rec = slugs[slug_]
                        if item.get("id") != rec.get("id"):
                            errs.append("%s: catalog id for %s is %r, record is %r"
                                        % (where, slug_, item.get("id"), rec.get("id")))
                validate_blog(doc.get("blog"), where, errs)
                texts = []
                _strings(doc, texts)
                for text in texts:
                    for match in LP_TOKEN.finditer(text):
                        tok = match.group(1)
                        if tok not in slugs:
                            errs.append("%s: {lp:%s} does not resolve" % (where, tok))
                continue
            validate_teaching_shape(doc, where, errs)
            validate_blog(doc.get("blog"), where, errs)
            stem = filename[:-5]
            if doc.get("slug") != stem:
                errs.append("%s: slug %r does not match the filename"
                            % (where, doc.get("slug")))
            if stem not in slugs:
                errs.append("%s: slug %r is not a principle of %s" % (where, stem, company))
            elif doc.get("id") != slugs[stem].get("id"):
                errs.append("%s: id %r does not match the principle record"
                            % (where, doc.get("id")))
            related = []
            rels = doc.get("related")
            if isinstance(rels, list):
                for rel in rels:
                    if not isinstance(rel, dict) or not _nonempty_str(rel.get("note")):
                        errs.append("%s: related entry needs an id and a note" % where)
                        rid = rel.get("id") if isinstance(rel, dict) else None
                    else:
                        rid = rel.get("id")
                    if rid not in slugs:
                        errs.append("%s: related id %r does not exist" % (where, rid))
                    else:
                        related.append(rid)
            texts = []
            for key in TEACH_PROSE:
                if key in doc:
                    _strings(doc[key], texts)
            for text in texts:
                for match in LP_TOKEN.finditer(text):
                    tok = match.group(1)
                    if tok not in slugs:
                        errs.append("%s: {lp:%s} does not resolve" % (where, tok))
                    elif tok not in related:
                        errs.append("%s: {lp:%s} is missing from related" % (where, tok))


def _record_by_id(by_company, company):
    out = {}
    for _, rec in by_company.get(company, []):
        pid = rec.get("id")
        if isinstance(pid, int) and not isinstance(pid, bool):
            out[pid] = rec
    return out


def _map_strings(obj, fn):
    if isinstance(obj, dict):
        return {k: _map_strings(v, fn) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_map_strings(v, fn) for v in obj]
    if isinstance(obj, str):
        return fn(obj)
    return obj


def _collect_strings(obj, out):
    if isinstance(obj, dict):
        for v in obj.values():
            _collect_strings(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _collect_strings(v, out)
    elif isinstance(obj, str):
        out.append(obj)


def _first_diff(a, b, path):
    if type(a) != type(b):
        return "%s: type" % path
    if isinstance(a, dict):
        if set(a) != set(b):
            return "%s: keys" % path
        for k in a:
            found = _first_diff(a[k], b[k], "%s.%s" % (path, k))
            if found:
                return found
        return None
    if isinstance(a, list):
        if len(a) != len(b):
            return "%s: length" % path
        for i, (x, y) in enumerate(zip(a, b)):
            found = _first_diff(x, y, "%s[%d]" % (path, i))
            if found:
                return found
        return None
    if a != b:
        return path
    return None


def _load_json(path, where, errs):
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except ValueError as e:
        errs.append("%s: not valid JSON, %s" % (where, e))
        return None
    if not isinstance(doc, dict):
        errs.append("%s: must be an object" % where)
        return None
    return doc


def validate_derivation_maps(by_company, principle_to_facets, errs, root=None):
    """A source set may reuse a target set's facets and teaching.

    data/maps/<source>-<target>.json names both companies. Lookups and
    teaching paths use those ids. Sentence changes are an allowlist on the
    map. Everything else in the reused teaching must match the target,
    aside from the source principle's id and slug.
    """
    data = root or DATA
    maps_dir = os.path.join(data, "maps")
    if not os.path.isdir(maps_dir):
        errs.append("data/maps is missing")
        return
    names = [n for n in sorted(os.listdir(maps_dir)) if not n.startswith(".")]
    if not names:
        errs.append("data/maps has no derivation map")
        return
    for name in names:
        where = "data/maps/%s" % name
        if not name.endswith(".json") or not os.path.isfile(os.path.join(maps_dir, name)):
            errs.append("%s: only .json maps belong here" % where)
            continue
        _validate_one_map(data, name, by_company, principle_to_facets, errs)


def _validate_one_map(data, name, by_company, principle_to_facets, errs):
    where = "data/maps/%s" % name
    doc = _load_json(os.path.join(data, "maps", name), where, errs)
    if doc is None:
        return
    check_style(doc, where, errs)
    if doc.get("version") != 1:
        errs.append("%s: version must be 1" % where)
    source_id = doc.get("source")
    target_id = doc.get("target")
    if not isinstance(source_id, str) or source_id not in by_company:
        errs.append("%s: source must name a company in this corpus" % where)
        return
    if not isinstance(target_id, str) or target_id not in by_company:
        errs.append("%s: target must name a company in this corpus" % where)
        return
    if name != "%s-%s.json" % (source_id, target_id):
        errs.append("%s: file name must be %s-%s.json" % (where, source_id, target_id))
    source_recs = _record_by_id(by_company, source_id)
    target_recs = _record_by_id(by_company, target_id)
    edits = doc.get("edits")
    if not isinstance(edits, list) or any(
            not isinstance(pair, list) or len(pair) != 2
            or not _nonempty_str(pair[0]) or not _nonempty_str(pair[1])
            or pair[0] == pair[1] for pair in edits):
        errs.append("%s: edits must be a list of [before, after] string pairs" % where)
        edits = []
    left = doc.get("leftOut")
    if not isinstance(left, list) or not left:
        errs.append("%s: leftOut must name target principles with no source counterpart" % where)
    else:
        for item in left:
            if (not isinstance(item, dict) or not _nonempty_str(item.get("name"))
                    or not _nonempty_str(item.get("reason"))):
                errs.append("%s: leftOut entries need a name and a reason" % where)
    pairs = doc.get("pairs")
    if not isinstance(pairs, list) or not pairs:
        errs.append("%s: pairs must be a non-empty list" % where)
        return
    seen = set()
    renames = []
    comparable = []
    for i, pair in enumerate(pairs):
        pw = "%s pairs[%d]" % (where, i)
        if not isinstance(pair, dict):
            errs.append("%s: must be an object" % pw)
            continue
        sid = pair.get("sourceId")
        if sid not in source_recs:
            errs.append("%s: sourceId %r is not a %s principle" % (pw, sid, source_id))
            continue
        if sid in seen:
            errs.append("%s: duplicate sourceId %s" % (pw, sid))
        seen.add(sid)
        rec = source_recs[sid]
        if pair.get("sourceSlug") != rec.get("slug"):
            errs.append("%s: slug %r does not match %s"
                        % (pw, pair.get("sourceSlug"), rec.get("slug")))
        if pair.get("sourceName") != rec.get("name"):
            errs.append("%s: name does not match the record" % pw)
        target_ids = pair.get("targetIds")
        if not isinstance(target_ids, list) or any(
                not isinstance(x, int) or isinstance(x, bool) for x in target_ids):
            errs.append("%s: targetIds must be a list of ids" % pw)
            target_ids = []
        if len(target_ids) != len(set(target_ids)):
            errs.append("%s: targetIds repeats an id" % pw)
        for tid in target_ids:
            if tid not in target_recs:
                errs.append("%s: target id %s is not in this corpus" % (pw, tid))
        facets = pair.get("facets")
        if not isinstance(facets, list) or any(not isinstance(x, str) for x in facets):
            errs.append("%s: facets must be a list of facet ids" % pw)
            facets = []
        actual = sorted(principle_to_facets.get(sid, []))
        if sorted(facets) != actual:
            errs.append("%s: facets %s do not match the facet map %s"
                        % (pw, sorted(facets), actual))
        counterpart = []
        for tid in target_ids:
            if tid in target_recs:
                counterpart.extend(principle_to_facets.get(tid, []))
        # A pair with no target has no facet set to copy. Its facets are
        # authored, and the check above already matches them to the map.
        if target_ids and sorted(set(counterpart)) != actual:
            errs.append("%s: facets are not the target's facets" % pw)
        flags = pair.get("rowFlags")
        if not isinstance(flags, list):
            errs.append("%s: rowFlags must be a list" % pw)
        else:
            for flag in flags:
                if (not isinstance(flag, dict) or not _nonempty_str(flag.get("facet"))
                        or not _nonempty_str(flag.get("row"))
                        or not _nonempty_str(flag.get("reason"))):
                    errs.append("%s: a row flag needs facet, row, and reason" % pw)
        public = pair.get("publicCounterpart")
        in_corpus = pair.get("inThisCorpus", True)
        if target_ids and in_corpus is False:
            errs.append("%s: inThisCorpus is false while targetIds is set" % pw)
        if not target_ids:
            if in_corpus is not False or not _nonempty_str(public):
                errs.append("%s: a pair with no target id needs publicCounterpart "
                            "and inThisCorpus false" % pw)
            # No target to copy. A teaching file here is authored from the
            # principle's own definition. validate_teaching checks that file.
            # It is not a reused document and it is not diffed against a target.
            continue
        if len(target_ids) != 1 or target_ids[0] not in target_recs:
            errs.append("%s: teaching reuse needs exactly one target principle" % pw)
            continue
        target_rec = target_recs[target_ids[0]]
        if rec.get("slug") != target_rec.get("slug"):
            renames.append((target_rec["slug"], rec["slug"]))
        comparable.append((pw, rec, target_rec))
    missing = sorted(set(source_recs) - seen)
    for sid in missing:
        errs.append("%s: %s principle %s has no pair" % (where, source_id, sid))
    _compare_reused_teaching(
        data, source_id, target_id, comparable, renames, edits, where, errs)


def _compare_reused_teaching(data, source_id, target_id, comparable, renames, edits, where, errs):
    """Copied teaching matches the target after the allowlist and slug renames."""
    renames = sorted(set(renames), key=lambda item: len(item[0]), reverse=True)

    def apply_text(text):
        for old, new in renames:
            text = text.replace(old, new)
        for before, after in edits:
            text = text.replace(before, after)
        return text

    target_blobs = []
    source_blobs = []

    def take(company, slug):
        path = os.path.join(data, "teaching", company, slug + ".json")
        label = "data/teaching/%s/%s.json" % (company, slug)
        if not os.path.isfile(path):
            return None, label
        return _load_json(path, label, errs), label

    for pw, rec, target_rec in comparable:
        src, src_label = take(source_id, rec["slug"])
        dst, dst_label = take(target_id, target_rec["slug"])
        if dst is None:
            if src is not None:
                errs.append("%s: teaching exists without a target teaching file" % pw)
            continue
        if src is None:
            errs.append("%s: missing reused teaching %s" % (pw, rec["slug"]))
            continue
        _collect_strings(dst, target_blobs)
        _collect_strings(src, source_blobs)
        got = _map_strings(dst, apply_text)
        got["id"] = rec["id"]
        diff = _first_diff(got, src, rec["slug"])
        if diff:
            errs.append("%s: reused teaching differs from %s at %s"
                        % (pw, target_rec["slug"], diff))

    src_index_path = os.path.join(data, "teaching", source_id, "index.json")
    dst_index_path = os.path.join(data, "teaching", target_id, "index.json")
    src_index = _load_json(src_index_path, "data/teaching/%s/index.json" % source_id, errs)
    dst_index = _load_json(dst_index_path, "data/teaching/%s/index.json" % target_id, errs)
    if isinstance(src_index, dict) and isinstance(dst_index, dict):
        src_index = dict(src_index)
        dst_index = dict(dst_index)
        src_index.pop("principles", None)
        dst_index.pop("principles", None)
        _collect_strings(dst_index, target_blobs)
        _collect_strings(src_index, source_blobs)
        got = _map_strings(dst_index, apply_text)
        diff = _first_diff(got, src_index, "index")
        if diff:
            errs.append("%s: set teaching index differs from the target at %s" % (where, diff))
    elif os.path.isfile(dst_index_path) and not os.path.isfile(src_index_path):
        errs.append("%s: missing reused set teaching index" % where)

    target_text = "\n".join(target_blobs)
    source_text = "\n".join(source_blobs)
    for before, after in edits:
        if before not in target_text:
            errs.append("%s: allowlisted edit is not in the target teaching: %r"
                        % (where, before[:80]))
        if after not in source_text:
            errs.append("%s: allowlisted edit is not in the source teaching: %r"
                        % (where, after[:80]))


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

    validate_teaching(by_company, errs)

    # Validate facets.json
    facets = load_facets(errs)
    principle_to_facets = validate_facets(facets, principle_rows, errs)
    names = {}
    for company, items in by_company.items():
        for _, rec in items:
            pid = rec.get("id")
            if isinstance(pid, int) and not isinstance(pid, bool):
                names[pid] = "%s/%s (%d %s)" % (
                    company, rec.get("slug"), pid, rec.get("name"))
    validate_calibration_coverage(
        facets, principle_rows, principle_to_facets, names, errs)
    validate_derivation_maps(by_company, principle_to_facets, errs)

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
            want = expected_index(by_company, principle_to_facets, errs)
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
