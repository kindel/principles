#!/usr/bin/env python3
"""Tenets and principles are never called stands.

The words are "tenet" and "principle", and they are synonyms here. This
repo's prose leaks into the apps that mount it and into agent prompts, so
the wording is checked, not remembered. Company text under data/ is the
company's own and is not scanned.
"""

import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROSE = ("README.md", "SCHEMA.md", os.path.join("tests", "README.md"))

# "stand" or "stands" as a noun: a determiner directly in front. The verb
# ("the company's grammar stand") has no determiner before it, and the word
# boundary keeps standard, standards, standalone, and understand out.
NOUN_STAND = re.compile(
    r"\b(?:a|the|its|their|our|this|that|one|another)\s+stands?\b",
    re.IGNORECASE)


class ProseTest(unittest.TestCase):
    """A tenet is a tenet or a principle, never a stand."""

    def test_no_prose_calls_a_tenet_a_stand(self):
        hits = []
        for rel in PROSE:
            with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
                for n, line in enumerate(f, 1):
                    m = NOUN_STAND.search(line)
                    if m:
                        hits.append("%s:%d: %r" % (rel, n, m.group(0)))
        self.assertEqual(
            [], hits, "prose calls a tenet a stand:\n" + "\n".join(hits))


if __name__ == "__main__":
    unittest.main()
