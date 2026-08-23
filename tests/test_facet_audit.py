#!/usr/bin/env python3
"""The facet-map audit stays complete, and the checker still catches a miss.

Unmapped now means an empty table. A principle that lands without a map, skip,
or new-facet decision is the miss this file exists to prevent. Each test
below plants one violation and asserts it is caught, then the corpus test
runs the checker over the real audit.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "scripts"))

from facet_audit import check_audit, load_corpus_inputs


def entry(pid, decision, reason="A one line reason.", **kw):
    e = {"id": pid, "decision": decision, "reason": reason}
    e.update(kw)
    return e


def audit(*entries):
    return {"version": 1, "principles": list(entries)}


class FacetAuditCheckerTest(unittest.TestCase):
    """Plant one violation per rule the checker claims to enforce."""

    PRINCIPLES = {1001, 1002, 7001}
    FACETS = {"customer-obsession", "think-big"}
    MEMBERSHIP = {1001: {"customer-obsession"}, 7001: {"think-big"}}

    def check(self, doc, principles=None, membership=None, facet_ids=None):
        return check_audit(
            doc,
            principles if principles is not None else set(self.PRINCIPLES),
            membership if membership is not None else dict(self.MEMBERSHIP),
            facet_ids if facet_ids is not None else set(self.FACETS),
        )

    def assertCaught(self, doc, fragment, **kw):
        errs = self.check(doc, **kw)
        self.assertTrue(
            any(fragment in e for e in errs),
            "expected an error mentioning %r, got %r" % (fragment, errs),
        )

    def good(self):
        return audit(
            entry(1001, "map", facets=["customer-obsession"]),
            entry(1002, "skip"),
            entry(7001, "map", facets=["think-big"], toyota="keep"),
        )

    def test_a_complete_audit_passes(self):
        self.assertEqual([], self.check(self.good()))

    def test_a_missing_principle_is_caught(self):
        doc = audit(
            entry(1001, "map", facets=["customer-obsession"]),
            entry(7001, "map", facets=["think-big"], toyota="keep"),
        )
        self.assertCaught(doc, "principle 1002 has no audit entry")

    def test_an_unknown_principle_is_caught(self):
        doc = audit(
            entry(1001, "map", facets=["customer-obsession"]),
            entry(1002, "skip"),
            entry(7001, "map", facets=["think-big"], toyota="keep"),
            entry(1099, "skip"),
        )
        self.assertCaught(doc, "audit 1099 is not a principle")

    def test_a_duplicate_entry_is_caught(self):
        doc = audit(
            entry(1001, "map", facets=["customer-obsession"]),
            entry(1001, "skip"),
            entry(1002, "skip"),
            entry(7001, "map", facets=["think-big"], toyota="keep"),
        )
        self.assertCaught(doc, "duplicate audit entry")

    def test_an_unknown_decision_is_caught(self):
        doc = audit(
            entry(1001, "maybe", facets=["customer-obsession"]),
            entry(1002, "skip"),
            entry(7001, "map", facets=["think-big"], toyota="keep"),
        )
        self.assertCaught(doc, "decision must be one of")

    def test_a_missing_reason_is_caught(self):
        doc = audit(
            entry(1001, "map", reason="", facets=["customer-obsession"]),
            entry(1002, "skip"),
            entry(7001, "map", facets=["think-big"], toyota="keep"),
        )
        self.assertCaught(doc, "reason is missing")

    def test_an_em_dash_in_a_reason_is_caught(self):
        doc = audit(
            entry(1001, "map", reason="Source — keep it.",
                  facets=["customer-obsession"]),
            entry(1002, "skip"),
            entry(7001, "map", facets=["think-big"], toyota="keep"),
        )
        self.assertCaught(doc, "em dash")

    def test_map_requires_facets(self):
        doc = audit(
            entry(1001, "map"),
            entry(1002, "skip"),
            entry(7001, "map", facets=["think-big"], toyota="keep"),
        )
        self.assertCaught(doc, "map requires facets")

    def test_map_to_an_unknown_facet_is_caught(self):
        doc = audit(
            entry(1001, "map", facets=["not-a-facet"]),
            entry(1002, "skip"),
            entry(7001, "map", facets=["think-big"], toyota="keep"),
        )
        self.assertCaught(doc, "unknown facet")

    def test_a_done_map_that_is_not_on_the_facet_is_caught(self):
        doc = audit(
            entry(1001, "map", facets=["customer-obsession"]),
            entry(1002, "map", facets=["customer-obsession"]),
            entry(7001, "map", facets=["think-big"], toyota="keep"),
        )
        self.assertCaught(doc, "map is not on")

    def test_a_done_map_on_an_unlisted_facet_is_caught(self):
        membership = {
            1001: {"customer-obsession", "think-big"},
            7001: {"think-big"},
        }
        self.assertCaught(self.good(), "unlisted", membership=membership)

    def test_a_pending_map_that_has_already_landed_is_caught(self):
        doc = audit(
            entry(1001, "map", facets=["customer-obsession"], pending=True),
            entry(1002, "skip"),
            entry(7001, "map", facets=["think-big"], toyota="keep"),
        )
        self.assertCaught(doc, "pending map is already on")

    def test_a_pending_map_that_has_not_landed_passes(self):
        doc = audit(
            entry(1001, "map", facets=["customer-obsession"]),
            entry(1002, "map", facets=["think-big"], pending=True),
            entry(7001, "map", facets=["think-big"], toyota="keep"),
        )
        self.assertEqual([], self.check(doc))

    def test_skip_must_not_list_facets(self):
        doc = audit(
            entry(1001, "map", facets=["customer-obsession"]),
            entry(1002, "skip", facets=["think-big"]),
            entry(7001, "map", facets=["think-big"], toyota="keep"),
        )
        self.assertCaught(doc, "skip must not list facets")

    def test_skip_that_is_still_mapped_is_caught(self):
        membership = {
            1001: {"customer-obsession"},
            1002: {"think-big"},
            7001: {"think-big"},
        }
        self.assertCaught(self.good(), "skip is still on",
                          membership=membership)

    def test_new_facet_requires_new_facets(self):
        doc = audit(
            entry(1001, "map", facets=["customer-obsession"]),
            entry(1002, "new-facet"),
            entry(7001, "map", facets=["think-big"], toyota="keep"),
        )
        self.assertCaught(doc, "new-facet requires new_facets")

    def test_new_facet_that_already_exists_is_caught(self):
        doc = audit(
            entry(1001, "map", facets=["customer-obsession"]),
            entry(1002, "new-facet", new_facets=["think-big"]),
            entry(7001, "map", facets=["think-big"], toyota="keep"),
        )
        self.assertCaught(doc, "already exists")

    def test_new_facet_must_not_also_map_to_an_existing_facet(self):
        doc = audit(
            entry(1001, "map", facets=["customer-obsession"]),
            entry(1002, "new-facet", facets=["think-big"],
                  new_facets=["frugality"]),
            entry(7001, "map", facets=["think-big"], toyota="keep"),
        )
        self.assertCaught(doc, "maps to no existing facet")

    def test_a_slice_may_map_and_name_a_new_facet(self):
        doc = audit(
            entry(1001, "map", facets=["customer-obsession"],
                  new_facets=["highest-standards"]),
            entry(1002, "skip"),
            entry(7001, "map", facets=["think-big"], toyota="keep"),
        )
        self.assertEqual([], self.check(doc))

    def test_a_toyota_entry_must_keep_or_revert(self):
        doc = audit(
            entry(1001, "map", facets=["customer-obsession"]),
            entry(1002, "skip"),
            entry(7001, "map", facets=["think-big"]),
        )
        self.assertCaught(doc, "toyota to keep or revert")

    def test_keep_must_be_map(self):
        doc = audit(
            entry(1001, "map", facets=["customer-obsession"]),
            entry(1002, "skip"),
            entry(7001, "skip", toyota="keep"),
        )
        self.assertCaught(doc, "keep must be map")

    def test_revert_must_be_skip(self):
        doc = audit(
            entry(1001, "map", facets=["customer-obsession"]),
            entry(1002, "skip"),
            entry(7001, "map", facets=["think-big"], toyota="revert"),
        )
        self.assertCaught(doc, "revert must be skip")

    def test_non_toyota_must_not_carry_toyota(self):
        doc = audit(
            entry(1001, "map", facets=["customer-obsession"], toyota="keep"),
            entry(1002, "skip"),
            entry(7001, "map", facets=["think-big"], toyota="keep"),
        )
        self.assertCaught(doc, "toyota is only for Toyota")


class FacetAuditCorpusTest(unittest.TestCase):
    """The written pass covers every current principle and matches the map."""

    def test_the_corpus_audit_passes(self):
        errs = check_audit(*load_corpus_inputs())
        self.assertEqual([], errs, "facet audit failed:\n" + "\n".join(errs))

    def test_pending_maps_are_the_named_follow_ons(self):
        audit, _, membership, _ = load_corpus_inputs()
        pending = sorted(
            (e["id"], tuple(e["facets"]))
            for e in audit["principles"]
            if e.get("pending")
        )
        self.assertEqual(
            [
                (3011, ("think-big",)),
            ],
            pending,
        )
        for pid, _facets in pending:
            self.assertNotIn(pid, membership)

    def test_named_new_facets_do_not_exist_yet(self):
        audit, _, _, facet_ids = load_corpus_inputs()
        named = sorted({
            fid
            for e in audit["principles"]
            for fid in e.get("new_facets", [])
        })
        self.assertEqual(
            [
                "deliver-results",
                "frugality",
                "highest-standards",
                "learn-and-be-curious",
            ],
            named,
        )
        for fid in named:
            self.assertNotIn(fid, facet_ids)

    def test_reverted_toyota_maps_are_gone(self):
        audit, _, membership, _ = load_corpus_inputs()
        reverted = [e["id"] for e in audit["principles"]
                    if e.get("toyota") == "revert"]
        self.assertEqual([7004, 7005], reverted)
        for pid in reverted:
            self.assertNotIn(pid, membership)

    def test_kept_toyota_maps_are_still_on_the_facet(self):
        audit, _, membership, _ = load_corpus_inputs()
        kept = {
            e["id"]: set(e["facets"])
            for e in audit["principles"]
            if e.get("toyota") == "keep"
        }
        self.assertEqual(
            {
                7001: {"think-big"},
                7002: {"better-every-day"},
                7003: {"dive-deep"},
            },
            kept,
        )
        for pid, facets in kept.items():
            self.assertEqual(facets, membership.get(pid, set()))


if __name__ == "__main__":
    unittest.main()
