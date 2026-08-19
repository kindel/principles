#!/usr/bin/env python3
"""The corpus itself, and the human-written calibration it is checked against.

`test_validate.py` proves the validator still enforces the rules. This file is
about the data: that it passes, that the quotations in it are still quotations,
and that nobody's words have been quietly borrowed.

`fixtures/dawn-company-tenets.json` is the reference. See README.md in this
directory for what it is and why a copy lives here.
"""

import io
import json
import os
import re
import sys
import unittest
from contextlib import redirect_stdout

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import validate
from companies import COMPANY_META

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
DATA = os.path.join(ROOT, "data")
SETTINGS = ("under", "justRight", "over")

# Wide enough that ordinary shared phrasing does not trip it, narrow enough
# that reordering a sentence does not hide a copy.
SHINGLE = 8
WORD = re.compile(r"[a-z0-9']+")


def shingles(text):
    w = WORD.findall(text.lower())
    return {" ".join(w[i:i + SHINGLE]) for i in range(len(w) - SHINGLE + 1)}


def load_fixtures():
    out = {}
    for name in sorted(os.listdir(FIXTURES)):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(FIXTURES, name), encoding="utf-8") as f:
            doc = json.load(f)
        out[doc["company"]["id"]] = doc
    return out


def load_rows():
    for company in sorted(os.listdir(DATA)):
        d = os.path.join(DATA, company)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not name.endswith(".json"):
                continue
            with open(os.path.join(d, name), encoding="utf-8") as f:
                doc = json.load(f)
            for row in doc.get("rows", []):
                yield "data/%s/%s:%s" % (company, name, row.get("id")), doc, row


class CorpusTest(unittest.TestCase):

    def test_the_corpus_validates(self):
        with redirect_stdout(io.StringIO()) as out:
            code = validate.main()
        self.assertEqual(0, code, "scripts/validate.py failed:\n" + out.getvalue())


class FixtureTest(unittest.TestCase):
    """The fixture is only worth testing against if it is intact."""

    def setUp(self):
        self.fixtures = load_fixtures()

    def test_there_is_at_least_one(self):
        self.assertTrue(self.fixtures, "no fixtures in tests/fixtures/")

    def test_every_entry_is_a_complete_triple(self):
        for company, doc in self.fixtures.items():
            for p in doc["principles"]:
                for key in SETTINGS:
                    self.assertTrue(
                        p["expected"].get(key),
                        "%s/%s is missing %s" % (company, p["slug"], key))

    def test_sort_is_one_through_n_with_no_gaps(self):
        for company, doc in self.fixtures.items():
            sorts = sorted(p["sort"] for p in doc["principles"])
            self.assertEqual(list(range(1, len(sorts) + 1)), sorts, company)

    def test_the_named_traps_exist(self):
        for company, doc in self.fixtures.items():
            slugs = {p["slug"] for p in doc["principles"]}
            for trap in doc.get("traps", []):
                self.assertIn(trap["principle"], slugs, company)

    # The one that would be easy to lose in a reformat, and the one the whole
    # fixture is most valuable for: Dawn inverts the usual polarity, because
    # perfectionism is Scrappy not crappy's *under*, not its over.
    def test_dawn_scrappy_keeps_its_inverted_polarity(self):
        dawn = self.fixtures.get("dawn")
        self.assertIsNotNone(dawn, "the Dawn fixture is gone")
        p = next(x for x in dawn["principles"]
                 if x["slug"] == "scrappy-not-crappy")
        self.assertIn("only 'finished' when it's perfect", p["expected"]["under"])
        self.assertIn("hoping for the best", p["expected"]["over"])

    def test_dawn_fixture_is_source_not_a_hold_out(self):
        # These rows are the quality bar a generator should sound like, not a
        # set it must not read. heldOut: true told the opposite story.
        dawn = self.fixtures.get("dawn")
        self.assertIsNotNone(dawn, "the Dawn fixture is gone")
        self.assertFalse(dawn.get("heldOut"),
                         "Dawn fixture is still marked heldOut")
        hold = dawn.get("shape", {}).get("holdOut", "")
        self.assertIn("source", hold.lower())
        self.assertNotIn("must not read them as examples", hold.lower())


class QuotationTest(unittest.TestCase):
    """Quotations stay quotations, and nobody else's words become ours."""

    def setUp(self):
        self.fixtures = load_fixtures()
        self.rows = list(load_rows())

    def test_no_quoted_row_drifts_from_the_fixture(self):
        for where, doc, row in self.rows:
            if row.get("words") != "quoted":
                continue
            fixture = self.fixtures.get(doc["company"])
            if fixture is None:
                # A company may publish calibration we have no fixture for.
                # Nothing to compare against, and nothing to conclude.
                continue

            # A fixture covers its company's whole set, so a quoted row in a
            # record the fixture does not know about is a misspelled id, a
            # principle added since the snapshot, or a fixture that has fallen
            # behind. Skipping it would leave the quotation unchecked, which is
            # the one thing this test exists to prevent.
            expected = next(
                (p["expected"] for p in fixture["principles"]
                 if p["slug"] == doc["slug"]), None)
            self.assertIsNotNone(
                expected,
                "%s is quoted and %s has a fixture, but the fixture has no %r, "
                "so the quotation is unverified"
                % (where, doc["company"], doc["slug"]))

            for key in SETTINGS:
                self.assertEqual(
                    expected[key], row.get(key),
                    "%s %s has been edited away from the fixture" % (where, key))

    def test_no_authored_row_reuses_a_company_s_words(self):
        golden = []
        for company, doc in self.fixtures.items():
            for p in doc["principles"]:
                for key in SETTINGS:
                    golden.append(("%s/%s %s" % (company, p["slug"], key),
                                   shingles(p["expected"][key])))

        for where, _, row in self.rows:
            if row.get("words") == "quoted":
                continue
            for key in SETTINGS:
                if not row.get(key):
                    continue
                mine = shingles(row[key])
                for gwhere, gshingles in golden:
                    shared = mine & gshingles
                    if shared:
                        self.fail("%s %s reuses %s: %r"
                                  % (where, key, gwhere, sorted(shared)[0]))


class DocumentationTest(unittest.TestCase):
    """SCHEMA.md is the contract. Code that has moved on from it is a lie."""

    def setUp(self):
        with open(os.path.join(ROOT, "SCHEMA.md"), encoding="utf-8") as f:
            self.schema = f.read()

    def test_schema_lists_the_companies_that_exist(self):
        listed = re.search(r"Current companies\s*\n?\s*are ([^.]+)\.", self.schema)
        self.assertIsNotNone(listed, "SCHEMA.md no longer lists the companies")
        named = set(re.findall(r"`([a-z-]+)`", listed.group(1)))
        self.assertEqual(set(COMPANY_META), named)

    def test_schema_lists_the_block_each_company_owns(self):
        for cid, meta in COMPANY_META.items():
            self.assertIn(
                str(meta["block"]), self.schema,
                "SCHEMA.md does not name %s's block, %d" % (cid, meta["block"]))

    def test_schema_describes_every_value_words_accepts(self):
        for value in validate.WORDS:
            self.assertIn("`%s`" % value, self.schema,
                          "SCHEMA.md does not mention words value %r" % value)

    def test_schema_names_the_manifest_version(self):
        self.assertIn("`version` in the manifest is 5", self.schema)

    def test_schema_does_not_treat_a_source_ref_as_an_app_row(self):
        # A refs-only facet is valid source. It is not the porridge table.
        # "either kind" implied the two row types were interchangeable for
        # display, which hid that generated rows may still be absent.
        self.assertNotIn("of either kind", self.schema)
        self.assertIn("may be absent", self.schema)
        self.assertIn("does not fall back", self.schema)


class AgentsDocTest(unittest.TestCase):
    """AGENTS.md is the ops checklist. A consumer the cascade pings that
    this file does not name will be skipped the next time a company lands.
    """

    def test_agents_md_names_every_cascade_consumer(self):
        agents_path = os.path.join(ROOT, "AGENTS.md")
        self.assertTrue(os.path.exists(agents_path), "AGENTS.md is missing")
        with open(agents_path, encoding="utf-8") as f:
            agents = f.read()
        consumers = os.path.join(ROOT, ".kindel", "consumers.txt")
        with open(consumers, encoding="utf-8") as f:
            lines = f.readlines()
        named = 0
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            repo = line.split()[0]
            self.assertIn(
                repo, agents,
                "AGENTS.md does not mention cascade consumer %s" % repo)
            named += 1
        self.assertGreater(named, 0, ".kindel/consumers.txt has no targets")


if __name__ == "__main__":
    unittest.main()
