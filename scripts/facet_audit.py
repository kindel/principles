#!/usr/bin/env python3
"""The facet-map audit: every principle is map, skip, or new-facet.

Unmapped now means an empty calibration table, so an unreviewed principle is
a silent miss. tests/fixtures/facet-audit.json is the written pass. This
file is the check that fails when a principle is added, mapped, or unmapped
without updating that pass.

High confidence only, same bar as the first map. A pending map is a follow-on
change, not a dump into facets.json. A new facet is named here and not
created in the same change as the audit.
"""

import json
import os
import sys

from companies import COMPANY_META
from validate import BLOCK_SIZE, check_style

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
AUDIT_PATH = os.path.join(ROOT, "tests", "fixtures", "facet-audit.json")

DECISIONS = ("map", "skip", "new-facet")
TOYOTA_CALLS = ("keep", "revert")


def load_audit(path=None):
    with open(path or AUDIT_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_facet_ids_and_membership(facets=None):
    if facets is None:
        with open(os.path.join(DATA, "facets.json"), encoding="utf-8") as f:
            facets = json.load(f)
    facet_ids = set()
    membership = {}
    for fac in facets.get("facets", []):
        fid = fac.get("id")
        if not fid:
            continue
        facet_ids.add(fid)
        for pid in fac.get("principles", []):
            membership.setdefault(pid, set()).add(fid)
    return facet_ids, membership


def load_principle_ids(by_company=None):
    if by_company is None:
        ids = set()
        for cid in COMPANY_META:
            d = os.path.join(DATA, cid)
            if not os.path.isdir(d):
                continue
            for name in os.listdir(d):
                if not name.endswith(".json"):
                    continue
                with open(os.path.join(d, name), encoding="utf-8") as f:
                    rec = json.load(f)
                pid = rec.get("id")
                if isinstance(pid, int) and not isinstance(pid, bool):
                    ids.add(pid)
        return ids
    ids = set()
    for items in by_company.values():
        for _, rec in items:
            pid = rec.get("id")
            if isinstance(pid, int) and not isinstance(pid, bool):
                ids.add(pid)
    return ids


def toyota_block():
    lo = COMPANY_META["toyota"]["block"]
    return lo + 1, lo + BLOCK_SIZE


def is_toyota(pid):
    lo, hi = toyota_block()
    return lo <= pid < hi


def check_audit(audit, principle_ids, membership, facet_ids):
    """Return error strings. Empty means the audit matches the corpus."""
    errs = []
    if not isinstance(audit, dict):
        return ["audit is not an object"]
    if audit.get("version") != 1:
        errs.append("audit version must be 1")

    entries = audit.get("principles")
    if not isinstance(entries, list) or not entries:
        errs.append("audit has no principles")
        return errs

    seen = {}
    for i, entry in enumerate(entries):
        where = "audit[%d]" % i
        if not isinstance(entry, dict):
            errs.append("%s is not an object" % where)
            continue
        pid = entry.get("id")
        if not isinstance(pid, int) or isinstance(pid, bool):
            errs.append("%s: id is not a number" % where)
            continue
        where = "audit %d" % pid
        if pid in seen:
            errs.append("%s: duplicate audit entry (also at %s)"
                        % (where, seen[pid]))
            continue
        seen[pid] = "audit[%d]" % i
        check_entry(entry, pid, where, principle_ids, membership,
                    facet_ids, errs)

    missing = sorted(principle_ids - set(seen))
    extra = sorted(set(seen) - principle_ids)
    for pid in missing:
        errs.append("principle %d has no audit entry" % pid)
    for pid in extra:
        errs.append("audit %d is not a principle in the corpus" % pid)
    return errs


def check_entry(entry, pid, where, principle_ids, membership, facet_ids, errs):
    decision = entry.get("decision")
    if decision not in DECISIONS:
        errs.append("%s: decision must be one of %s"
                    % (where, ", ".join(DECISIONS)))
        return

    reason = entry.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        errs.append("%s: reason is missing" % where)
    else:
        check_style(reason, where + " reason", errs)

    facets = entry.get("facets", [])
    new_facets = entry.get("new_facets", [])
    pending = entry.get("pending", False)
    toyota = entry.get("toyota")

    if facets is None:
        facets = []
    if new_facets is None:
        new_facets = []
    if not isinstance(facets, list) or any(not isinstance(x, str) for x in facets):
        errs.append("%s: facets must be a list of facet ids" % where)
        return
    if (not isinstance(new_facets, list)
            or any(not isinstance(x, str) for x in new_facets)):
        errs.append("%s: new_facets must be a list of facet ids" % where)
        return
    if pending not in (True, False):
        errs.append("%s: pending must be true or false" % where)
        return

    if is_toyota(pid):
        if toyota not in TOYOTA_CALLS:
            errs.append("%s: Toyota entries must set toyota to keep or revert"
                        % where)
    elif toyota is not None:
        errs.append("%s: toyota is only for Toyota principles" % where)

    actual = set(membership.get(pid, ()))
    wanted = set(facets)

    for fid in facets:
        if fid not in facet_ids:
            errs.append("%s: maps to unknown facet %r" % (where, fid))
    for fid in new_facets:
        if fid in facet_ids:
            errs.append("%s: new_facets names %r, which already exists"
                        % (where, fid))

    if decision == "map":
        if not facets:
            errs.append("%s: map requires facets" % where)
        if pending:
            already = sorted(wanted & actual)
            if already:
                errs.append("%s: pending map is already on %s"
                            % (where, ", ".join(already)))
            extra = sorted(actual - wanted)
            if extra:
                errs.append("%s: pending map is also on unlisted %s"
                            % (where, ", ".join(extra)))
        else:
            missing = sorted(wanted - actual)
            extra = sorted(actual - wanted)
            if missing:
                errs.append("%s: map is not on %s"
                            % (where, ", ".join(missing)))
            if extra:
                errs.append("%s: map is also on unlisted %s"
                            % (where, ", ".join(extra)))
        if toyota == "revert":
            errs.append("%s: revert must be skip, not map" % where)
        if toyota == "keep" and pending:
            errs.append("%s: a kept Toyota map cannot be pending" % where)
    elif decision == "skip":
        if facets:
            errs.append("%s: skip must not list facets" % where)
        if new_facets:
            errs.append("%s: skip must not list new_facets" % where)
        if pending:
            errs.append("%s: skip cannot be pending" % where)
        if actual:
            errs.append("%s: skip is still on %s"
                        % (where, ", ".join(sorted(actual))))
        if toyota == "keep":
            errs.append("%s: keep must be map, not skip" % where)
    elif decision == "new-facet":
        if not new_facets:
            errs.append("%s: new-facet requires new_facets" % where)
        if facets:
            errs.append("%s: new-facet maps to no existing facet; use map "
                        "and new_facets for a principle that is already a "
                        "slice" % where)
        if pending:
            errs.append("%s: new-facet cannot be pending" % where)
        if actual:
            errs.append("%s: new-facet is already on %s"
                        % (where, ", ".join(sorted(actual))))
        if toyota == "keep":
            errs.append("%s: keep must be map, not new-facet" % where)


def load_corpus_inputs():
    principle_ids = load_principle_ids()
    facet_ids, membership = load_facet_ids_and_membership()
    audit = load_audit()
    return audit, principle_ids, membership, facet_ids


def main():
    audit, principle_ids, membership, facet_ids = load_corpus_inputs()
    errs = check_audit(audit, principle_ids, membership, facet_ids)
    if errs:
        for e in errs:
            print(e)
        print("%d audit error%s" % (len(errs), "" if len(errs) == 1 else "s"))
        return 1

    pending = []
    named = []
    seen_f = set()
    skips = 0
    mapped = 0
    new_facet_n = 0
    for entry in audit["principles"]:
        decision = entry["decision"]
        if decision == "skip":
            skips += 1
        elif decision == "map":
            mapped += 1
            if entry.get("pending"):
                pending.append("%d -> %s" % (
                    entry["id"], ", ".join(entry["facets"])))
        else:
            new_facet_n += 1
        for fid in entry.get("new_facets", []):
            if fid not in seen_f:
                seen_f.add(fid)
                named.append(fid)

    print("audit ok: %d principles, %d mapped, %d skip, %d new-facet"
          % (len(audit["principles"]), mapped, skips, new_facet_n))
    if pending:
        print("pending maps:")
        for line in pending:
            print("  %s" % line)
    if named:
        print("named new facets: %s" % ", ".join(named))
    return 0


if __name__ == "__main__":
    sys.exit(main())
