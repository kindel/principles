#!/usr/bin/env python3
"""The validator enforces what SCHEMA.md says.

`validate.py` is the only thing standing between the schema and a corpus that
quietly stops obeying it. A rule that stops being enforced does not announce
itself: the corpus keeps passing, and the drift shows up months later in an
app. That has happened once already. The Arm-only `group` rule was written
down, believed, and unenforced, and a record with an invented lens passed.

So each test here plants one violation and asserts it is caught. One test per
rule that has a consequence. Rules whose only consequence is tidiness are left
to review.
"""

import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "scripts"))

from companies import COMPANY_META
from validate import (expected_index, validate_company, validate_facets,
                      validate_record)


def row(i, **kw):
    r = {
        "id": "row-%d" % i,
        "situation": "A situation",
        "under": "Does not do it.",
        "justRight": "Does it well.",
        "over": "Does far too much of it.",
    }
    r.update(kw)
    return r


def record(company="amazon", rows=None, **kw):
    rec = {
        "id": 1001,
        "slug": "a-principle",
        "company": company,
        "name": "A Principle",
        "sort": 1,
        "definition": "The company's own short statement.",
        "terms": [],
        "rows": rows if rows is not None else [row(i) for i in range(5)],
    }
    rec.update(kw)
    return rec


class ValidatorTest(unittest.TestCase):

    def check(self, rec, company=None, filename="a-principle.json"):
        errs = []
        validate_record(company or rec["company"], filename, rec, errs)
        return errs

    def assertCaught(self, rec, fragment, **kw):
        errs = self.check(rec, **kw)
        self.assertTrue(
            any(fragment in e for e in errs),
            "expected an error mentioning %r, got %r" % (fragment, errs),
        )

    def assertClean(self, rec, **kw):
        self.assertEqual([], self.check(rec, **kw))

    # A record that obeys every rule must pass, or every test below is
    # meaningless.
    def test_a_good_record_passes(self):
        self.assertClean(record())

    def test_slug_must_match_the_filename(self):
        self.assertCaught(record(), "does not match the filename",
                          filename="something-else.json")

    def test_company_must_match_the_directory(self):
        rec = record(company="amazon")
        self.assertCaught(rec, "does not match the directory", company="coupang")

    # The id carries identity, so it is the one field that has to be a number
    # and has to sit in its owner's block. A string id is what version 2 had,
    # and a record still carrying one should say so plainly.
    def test_a_string_id_is_rejected(self):
        rec = record()
        rec["id"] = "a-principle"
        self.assertCaught(rec, "is not a number")

    def test_an_id_outside_the_company_block_is_rejected(self):
        rec = record(company="amazon")
        rec["id"] = 6004
        self.assertCaught(rec, "outside amazon's block")

    def test_the_block_boundaries_themselves_are_not_valid_ids(self):
        for pid in (1000, 2000):
            rec = record(company="amazon")
            rec["id"] = pid
            self.assertCaught(rec, "outside amazon's block")

    # A bool is an int in Python, and `id: true` should not pass for it.
    def test_a_boolean_id_is_rejected(self):
        rec = record()
        rec["id"] = True
        self.assertCaught(rec, "is not a number")

    # The rule that was written down and unenforced. Only companies that
    # publish their set under lenses carry `group`.
    def test_group_is_rejected_where_the_company_has_no_lenses(self):
        self.assertCaught(record(group="invented-lens"),
                          "do not carry group")

    def test_group_is_required_where_the_company_has_lenses(self):
        rec = record(company="arm")
        rec["id"] = 2001
        self.assertCaught(rec, "require group")

    def test_group_must_match_the_lens_the_sort_falls_in(self):
        rec = record(company="arm", sort=1, group="accelerate-impact")
        rec["id"] = 2001
        self.assertCaught(rec, "does not match sort")

    # The schema's one real claim is that a principle decomposes into behavior
    # you can observe. A record with no rows makes that claim and does not keep
    # it. How many rows past one is judgment, not a rule.
    def test_a_record_with_no_rows_is_rejected(self):
        self.assertCaught(record(rows=[]), "has no rows")

    def test_one_row_is_enough(self):
        self.assertClean(record(rows=[row(0)]))

    def test_many_rows_are_fine(self):
        self.assertClean(record(rows=[row(i) for i in range(20)]))

    def test_an_authored_row_may_not_run_long(self):
        rows = [row(i) for i in range(5)]
        rows[0]["justRight"] = "One. Two. Three. Four."
        self.assertCaught(record(rows=rows), "expected one to three")

    # Terminal punctuation inside a closing quote still ends a sentence. This
    # regression cost a rescan of the whole corpus.
    def test_a_sentence_break_after_a_closing_quote_counts(self):
        rows = [row(i) for i in range(5)]
        rows[0]["under"] = 'Is not "always." Seeks input. Then decides. And moves.'
        self.assertCaught(record(rows=rows), "expected one to three")

    # A quotation is the company's writing. The sentence rule is ours.
    def test_a_quoted_row_may_run_long(self):
        rows = [row(i, words="authored") for i in range(5)]
        rows[0]["words"] = "quoted"
        rows[0]["justRight"] = "One. Two. Three. Four. Five. Six. Seven. Eight."
        self.assertClean(record(rows=rows))

    def test_words_is_all_or_nothing_within_a_record(self):
        rows = [row(i) for i in range(5)]
        rows[0]["words"] = "quoted"
        self.assertCaught(record(rows=rows), "mark all of them or none")

    def test_words_must_be_a_known_value(self):
        self.assertCaught(record(rows=[row(i, words="borrowed") for i in range(5)]),
                          "expected one of")

    def test_generated_is_a_known_value(self):
        self.assertClean(record(rows=[row(i, words="generated") for i in range(5)]))

    # The em dash check is about what the file may contain, so it runs even on
    # a quotation, exactly as it does on `definition`.
    def test_an_em_dash_is_rejected_inside_a_quoted_row(self):
        rows = [row(i, words="authored") for i in range(5)]
        rows[0]["words"] = "quoted"
        rows[0]["over"] = "Far too much — always."
        self.assertCaught(record(rows=rows), "em dash")

    def test_a_facet_must_carry_rows(self):
        rec = record(terms=[{"id": "a-slice", "label": "a slice", "kind": "facet"}])
        self.assertCaught(rec, "carries no rows")

    def test_a_facet_may_not_point_at_a_row_that_does_not_exist(self):
        rec = record(terms=[{"id": "a-slice", "label": "a slice", "kind": "facet",
                             "rows": ["row-99"]}])
        self.assertCaught(rec, "unknown row")

    def test_a_term_id_must_be_the_slug_of_its_label(self):
        rec = record(terms=[{"id": "wrong", "label": "a slice", "kind": "equivalent"}])
        self.assertCaught(rec, "is not the slug of label")

    def test_duplicate_row_ids(self):
        rows = [row(i) for i in range(5)]
        rows[1]["id"] = rows[0]["id"]
        self.assertCaught(record(rows=rows), "duplicate row id")

    def test_a_row_may_not_be_missing_its_calibration(self):
        rows = [row(i) for i in range(5)]
        del rows[0]["over"]
        self.assertCaught(record(rows=rows), "missing 'over'")


class CompanyChecksTest(unittest.TestCase):
    """Checks that span a company's directory rather than one record.

    A malformed record has already been reported by validate_record. The
    company-level pass must still report its own rule readably instead of
    dying on the malformed value, or the contributor sees a traceback where
    the queued errors should have been.
    """

    def check(self, items, company="amazon"):
        errs = []
        validate_company(company, items, errs)
        return errs

    def test_a_complete_sequence_passes(self):
        items = [("a.json", record(sort=1)), ("b.json", record(sort=2))]
        self.assertEqual([], self.check(items))

    def test_a_gap_in_the_sorts_is_rejected(self):
        items = [("a.json", record(sort=1)), ("b.json", record(sort=3))]
        errs = self.check(items)
        self.assertTrue(any("sort must be one through 2" in e for e in errs),
                        errs)

    def test_a_missing_sort_is_an_error_not_a_traceback(self):
        rec = record()
        del rec["sort"]
        items = [("a.json", record(sort=1)), ("b.json", rec)]
        errs = self.check(items)
        self.assertTrue(any("sort must be one through" in e for e in errs),
                        errs)

    def test_a_non_numeric_sort_is_an_error_not_a_traceback(self):
        items = [("a.json", record(sort=1)), ("b.json", record(sort="2"))]
        errs = self.check(items)
        self.assertTrue(any("sort must be one through" in e for e in errs),
                        errs)

    def test_a_term_id_reused_across_records_is_rejected(self):
        terms = [{"id": "a-slice", "label": "a slice", "kind": "equivalent"}]
        items = [("a.json", record(sort=1, terms=copy.deepcopy(terms))),
                 ("b.json", record(sort=2, terms=copy.deepcopy(terms)))]
        errs = self.check(items)
        self.assertTrue(any("used by both" in e for e in errs), errs)


class ExpectedIndexTest(unittest.TestCase):
    """The stale-index comparison must survive a malformed record.

    validate_record has already queued the schema error for it; the index
    builder skipping the record keeps the run alive so those errors print.
    """

    def build(self, items):
        by_company = {cid: [] for cid in COMPANY_META}
        by_company["amazon"] = items
        return expected_index(by_company, {})

    def amazon(self, idx):
        return next(c for c in idx["companies"] if c["id"] == "amazon")

    def test_a_good_record_lands_in_the_index(self):
        idx = self.build([("a-principle.json", record())])
        self.assertEqual(["a-principle"],
                         [p["slug"] for p in self.amazon(idx)["principles"]])

    def test_a_record_missing_name_is_skipped_not_a_traceback(self):
        rec = record()
        del rec["name"]
        idx = self.build([("a-principle.json", rec)])
        self.assertEqual([], self.amazon(idx)["principles"])

    def test_a_record_missing_sort_is_skipped_not_a_traceback(self):
        rec = record()
        del rec["sort"]
        idx = self.build([("a-principle.json", rec)])
        self.assertEqual([], self.amazon(idx)["principles"])

    def test_a_non_numeric_sort_is_skipped_not_a_traceback(self):
        idx = self.build([("a-principle.json", record(sort="1")),
                          ("b-principle.json", record(sort=2, slug="b-principle",
                                                      name="B Principle", id=1002))])
        self.assertEqual(["b-principle"],
                         [p["slug"] for p in self.amazon(idx)["principles"]])

    def test_the_index_is_version_5(self):
        # Version 4 resolved {principle, id} refs into the display table.
        # Version 5 displays only inline generated rows. A silent reuse of 4
        # would leave consumers with no signal to stop showing human rows.
        idx = self.build([("a-principle.json", record())])
        self.assertEqual(5, idx["version"])


def facet(**kw):
    f = {
        "id": "a-facet",
        "label": "a facet",
        "principles": [1001],
        "rows": [{"principle": 1001, "id": "row-0"}],
    }
    f.update(kw)
    return f


class FacetMapTest(unittest.TestCase):
    """facets.json rows must come from principles the facet itself lists.

    A row from an unlisted principle renders on every member of the facet
    while its own principle never gets the facet in the index.
    """

    ROWS = {1001: {"row-0"}, 2001: {"row-x"}}

    def check(self, *facets):
        errs = []
        validate_facets({"version": 1, "facets": list(facets)}, self.ROWS, errs)
        return errs

    def test_a_good_facet_passes(self):
        self.assertEqual([], self.check(facet()))

    def test_a_row_from_an_unlisted_principle_is_rejected(self):
        f = facet(rows=[{"principle": 1001, "id": "row-0"},
                        {"principle": 2001, "id": "row-x"}])
        errs = self.check(f)
        self.assertTrue(
            any("not in this facet's principles" in e for e in errs), errs)

    def test_listing_the_principle_makes_the_same_row_legal(self):
        f = facet(principles=[1001, 2001],
                  rows=[{"principle": 1001, "id": "row-0"},
                        {"principle": 2001, "id": "row-x"}])
        self.assertEqual([], self.check(f))

    def test_an_inline_generated_row_passes(self):
        f = facet(rows=[
            {"principle": 1001, "id": "row-0"},
            {
                "id": "a-new-situation",
                "situation": "A new situation",
                "under": "Does not own it.",
                "justRight": "Owns it and finishes it.",
                "over": "Takes over everyone else's work.",
                "words": "generated",
            },
        ])
        self.assertEqual([], self.check(f))

    def test_a_generated_only_facet_is_rejected(self):
        # Generated rows are the app table. Source refs are what the
        # generator reads. A facet with only generated rows has lost its
        # source, so it cannot be regenerated.
        f = facet(rows=[{
            "id": "a-new-situation",
            "situation": "A new situation",
            "under": "Does not own it.",
            "justRight": "Owns it and finishes it.",
            "over": "Takes over everyone else's work.",
            "words": "generated",
        }])
        errs = self.check(f)
        self.assertTrue(any("at least one source ref" in e for e in errs), errs)

    def test_an_inline_row_must_be_marked_generated(self):
        f = facet(rows=[{
            "id": "a-new-situation",
            "situation": "A new situation",
            "under": "Does not own it.",
            "justRight": "Owns it and finishes it.",
            "over": "Takes over everyone else's work.",
            "words": "authored",
        }])
        errs = self.check(f)
        self.assertTrue(any("words must be generated" in e for e in errs), errs)

    def test_an_inline_row_must_not_name_a_principle(self):
        f = facet(rows=[{
            "id": "a-new-situation",
            "principle": 1001,
            "situation": "A new situation",
            "under": "Does not own it.",
            "justRight": "Owns it and finishes it.",
            "over": "Takes over everyone else's work.",
            "words": "generated",
        }])
        errs = self.check(f)
        self.assertTrue(any("must not name a principle" in e for e in errs), errs)

    def test_an_inline_row_still_needs_one_to_three_sentences(self):
        f = facet(rows=[{
            "id": "a-new-situation",
            "situation": "A new situation",
            "under": "One. Two. Three. Four.",
            "justRight": "Owns it.",
            "over": "Takes over.",
            "words": "generated",
        }])
        errs = self.check(f)
        self.assertTrue(any("one to three" in e for e in errs), errs)


if __name__ == "__main__":
    unittest.main()
