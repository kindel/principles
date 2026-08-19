#!/usr/bin/env python3
"""The facet map: same facet, same examples.

Principles that share a facet share the rows mapped to that facet. This file
tests that the map is wired correctly and that the index reflects it.
"""

import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")


def load_facets():
    with open(os.path.join(DATA, "facets.json"), encoding="utf-8") as f:
        return json.load(f)


def load_index():
    with open(os.path.join(DATA, "index.json"), encoding="utf-8") as f:
        return json.load(f)


def principle_facets_from_index(index, principle_id):
    """Return the facets array for a principle from the index."""
    for company in index["companies"]:
        for p in company["principles"]:
            if p["id"] == principle_id:
                return p.get("facets", [])
    return []


def facet_by_id(facets, facet_id):
    """Return the facet dict for a given facet id."""
    for f in facets["facets"]:
        if f["id"] == facet_id:
            return f
    return None


def rows_for_principle_on_facet(facet, principle_id):
    """Return the row ids mapped to a principle on a facet."""
    return [r["id"] for r in facet["rows"] if r["principle"] == principle_id]


class FacetSharingTest(unittest.TestCase):
    """Test that principles share facets as documented."""

    def setUp(self):
        self.facets = load_facets()
        self.index = load_index()

    def test_dawn_ownership_and_amazon_ownership_share_acts_like_an_owner(self):
        # Dawn 6004 and Amazon 1002 share acts-like-an-owner
        dawn_facets = principle_facets_from_index(self.index, 6004)
        amazon_facets = principle_facets_from_index(self.index, 1002)
        self.assertIn("acts-like-an-owner", dawn_facets)
        self.assertIn("acts-like-an-owner", amazon_facets)

    def test_dawn_better_than_yesterday_and_amazon_ihs_share_better_every_day(self):
        # Dawn 6009 and Amazon 1007 share better-every-day
        dawn_facets = principle_facets_from_index(self.index, 6009)
        amazon_facets = principle_facets_from_index(self.index, 1007)
        self.assertIn("better-every-day", dawn_facets)
        self.assertIn("better-every-day", amazon_facets)

    def test_better_every_day_is_a_slice_of_ihs_not_the_whole_list(self):
        # better-every-day is a slice: Dawn 6009 gets only the continuous
        # improvement rows of IHS, not all of them. catalog-quality is on IHS
        # but not on better-every-day.
        facet = facet_by_id(self.facets, "better-every-day")
        self.assertIsNotNone(facet)

        # The facet should have rows from 1007 (IHS) and 6009 (BTY)
        ihs_rows = rows_for_principle_on_facet(facet, 1007)
        bty_rows = rows_for_principle_on_facet(facet, 6009)

        # 1007 has tracking-goals and confronting-issues on this facet
        self.assertIn("tracking-goals", ihs_rows)
        self.assertIn("confronting-issues", ihs_rows)

        # 6009 has its own example
        self.assertIn("dawns-own-example", bty_rows)

        # catalog-quality is NOT on this facet (it stays IHS-only)
        self.assertNotIn("catalog-quality", ihs_rows)

    def test_acts_like_an_owner_includes_all_four_companies(self):
        # acts-like-an-owner maps Amazon 1002, Dawn 6004, Arm 2008, DH 4001
        facet = facet_by_id(self.facets, "acts-like-an-owner")
        self.assertIsNotNone(facet)
        self.assertEqual(sorted(facet["principles"]), [1002, 2008, 4001, 6004])

    def test_toyota_genchi_genbutsu_shares_dive_deep(self):
        # Toyota 7003 is the same go-and-see behavior as Amazon, Coupang,
        # and Delivery Hero Dive Deep.
        toyota_facets = principle_facets_from_index(self.index, 7003)
        amazon_facets = principle_facets_from_index(self.index, 1012)
        self.assertIn("dive-deep", toyota_facets)
        self.assertIn("dive-deep", amazon_facets)

    def test_toyota_challenge_shares_think_big(self):
        toyota_facets = principle_facets_from_index(self.index, 7001)
        amazon_facets = principle_facets_from_index(self.index, 1008)
        self.assertIn("think-big", toyota_facets)
        self.assertIn("think-big", amazon_facets)

    def test_toyota_kaizen_shares_better_every_day(self):
        # Toyota 7002 and Dawn 6009 share better-every-day
        toyota_facets = principle_facets_from_index(self.index, 7002)
        dawn_facets = principle_facets_from_index(self.index, 6009)
        self.assertIn("better-every-day", toyota_facets)
        self.assertIn("better-every-day", dawn_facets)

    def test_better_every_day_is_a_slice_of_kaizen_not_the_whole_list(self):
        # better-every-day takes Kaizen's daily-improvement rows, not the
        # replace-the-process one.
        facet = facet_by_id(self.facets, "better-every-day")
        self.assertIsNotNone(facet)
        kaizen_rows = rows_for_principle_on_facet(facet, 7002)
        self.assertIn("a-small-defect", kaizen_rows)
        self.assertIn("the-standard", kaizen_rows)
        self.assertNotIn("innovation-and-evolution", kaizen_rows)

    def test_facet_ids_in_index_match_facets_json(self):
        # Every facet id in the index should exist in facets.json
        facet_ids = {f["id"] for f in self.facets["facets"]}
        for company in self.index["companies"]:
            for p in company["principles"]:
                for fid in p.get("facets", []):
                    self.assertIn(fid, facet_ids,
                                  "principle %d lists unknown facet %r"
                                  % (p["id"], fid))


class FacetStructureTest(unittest.TestCase):
    """Basic structural tests for facets.json."""

    def setUp(self):
        self.facets = load_facets()

    def test_version_is_1(self):
        self.assertEqual(1, self.facets["version"])

    def test_every_facet_has_unique_id(self):
        ids = [f["id"] for f in self.facets["facets"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_facet_has_at_least_one_principle(self):
        for f in self.facets["facets"]:
            self.assertTrue(f["principles"],
                            "facet %r has no principles" % f["id"])

    def test_every_facet_has_at_least_one_row(self):
        for f in self.facets["facets"]:
            self.assertTrue(f["rows"],
                            "facet %r has no rows" % f["id"])


if __name__ == "__main__":
    unittest.main()
