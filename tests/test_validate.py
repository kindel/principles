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

from validate import validate_record


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
        "id": "a-principle",
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

    def test_id_must_match_the_filename(self):
        self.assertCaught(record(), "does not match the filename",
                          filename="something-else.json")

    def test_company_must_match_the_directory(self):
        rec = record(company="amazon")
        self.assertCaught(rec, "does not match the directory", company="coupang")

    # The rule that was written down and unenforced. Only companies that
    # publish their set under lenses carry `group`.
    def test_group_is_rejected_where_the_company_has_no_lenses(self):
        self.assertCaught(record(group="invented-lens"),
                          "do not carry group")

    def test_group_is_required_where_the_company_has_lenses(self):
        self.assertCaught(record(company="arm"), "require group")

    def test_group_must_match_the_lens_the_sort_falls_in(self):
        rec = record(company="arm", sort=1, group="accelerate-impact")
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


if __name__ == "__main__":
    unittest.main()
