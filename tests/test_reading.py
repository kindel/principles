#!/usr/bin/env python3
"""Every Further reading list carries at least one source beyond tig.log.

The `blog` field in data/teaching/<company> renders as Further reading in
Porridge (kindel/porridge#46). Essays are linked at
https://kindel.com/essays/<slug>/. Other tig.log posts stay on
blog.kindel.com. Each list also needs one external source: the published
principles, a shareholder letter, a book, or an essay or talk by someone
who shaped the practice. See SCHEMA.md.
Amazon is the classic 14. Any Company reuses those lists, and authors
Intentional About Culture because that counterpart is not in this corpus.
The generic catalog and Intentional About Culture also append culture
reading that is not on the Amazon copies. Every other company ships a
catalog and one reading-only file per principle.
"""

import json
import os
import unittest
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEACH = os.path.join(ROOT, "data", "teaching")
INDEX = os.path.join(ROOT, "data", "index.json")
BLOG_HOST = "blog.kindel.com"


def expected_counts():
    """One catalog plus one teaching file per principle, for every company."""
    with open(INDEX, encoding="utf-8") as f:
        idx = json.load(f)
    return {co["id"]: 1 + len(co["principles"]) for co in idx["companies"]}


def is_tig(url):
    """A tig.log post, whether it still lives on the blog or on /essays/."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if host == BLOG_HOST:
        return True
    if host != "kindel.com":
        return False
    path = parsed.path or ""
    return path == "/essays" or path.startswith("/essays/")


def lists(company=None):
    companies = [company] if company else list(expected_counts())
    for company in companies:
        d = os.path.join(TEACH, company)
        for name in sorted(os.listdir(d)):
            if name.endswith(".json"):
                with open(os.path.join(d, name), encoding="utf-8") as f:
                    yield "%s/%s" % (company, name), json.load(f).get("blog")


class FurtherReadingTest(unittest.TestCase):

    def test_every_list_has_an_external_source(self):
        for company, want in expected_counts().items():
            seen = 0
            for name, items in lists(company):
                seen += 1
                with self.subTest(file=name):
                    self.assertTrue(items, "blog list is missing or empty")
                    self.assertTrue(any(not is_tig(i["url"]) for i in items),
                                    "needs at least one source beyond tig.log")
            self.assertEqual(seen, want, company)

    def test_entries_have_the_same_shape(self):
        for name, items in lists():
            for i in items or []:
                with self.subTest(file=name, title=i.get("title")):
                    self.assertEqual(set(i), {"title", "url", "note"})
                    u = urlparse(i["url"])
                    self.assertEqual(u.scheme, "https")
                    self.assertTrue(u.hostname, "url needs a host")
                    self.assertTrue(i["title"].strip())
                    self.assertTrue(i["note"].strip())
                    for s in i.values():
                        self.assertNotIn("—", s, "no em dashes")

    def test_external_cites(self):
        # Tig set these cites. The published heading is sometimes only a
        # year or a short title, so the list names the author or the source,
        # and the work. The AWS cite names AWS, not an author.
        expected = {
            "https://www.aboutamazon.com/news/company-news/amazons-original-1997-letter-to-shareholders":
                ("Jeff Bezos's 1997 Letter to Amazon Shareholders", 2),
            "https://www.sec.gov/Archives/edgar/data/1018724/000119312510082914/dex991.htm":
                ("Jeff Bezos's 2009 Letter to Amazon Shareholders", 1),
            "https://ir.aboutamazon.com/files/doc_financials/annual/2015-Letter-to-Shareholders.PDF":
                ("Jeff Bezos's 2015 Letter to Amazon Shareholders", 2),
            "https://www.aboutamazon.com/news/company-news/2016-letter-to-shareholders":
                ("Jeff Bezos's 2016 Letter to Amazon Shareholders", 2),
            "https://www.aboutamazon.com/news/company-news/2017-letter-to-shareholders":
                ("Jeff Bezos's 2017 Letter to Amazon Shareholders", 1),
            "https://www.aboutamazon.com/news/company-news/2018-letter-to-shareholders":
                ("Jeff Bezos's 2018 Letter to Amazon Shareholders", 1),
            "https://us.macmillan.com/books/9781250267597/workingbackwards/":
                ("Working Backwards, the book by Colin Bryar and Bill Carr", 3),
            "https://www.amazon.jobs/content/en/our-workplace/leadership-principles":
                ("Amazon's Leadership Principles", 1),
            "https://signalvnoise.com/svn3/some-advice-from-jeff-bezos/":
                ("Jason Fried: Some Advice from Jeff Bezos", 1),
            "https://aws.amazon.com/blogs/mt/why-you-should-develop-a-correction-of-error-coe/":
                ("Why You Should Develop a Correction of Error (COE), from AWS", 1),
        }
        seen = {url: 0 for url in expected}
        for name, items in lists("amazon"):
            for item in items or []:
                url = item["url"]
                if url not in expected:
                    continue
                want, _n = expected[url]
                with self.subTest(file=name, url=url):
                    self.assertEqual(item["title"], want)
                    self.assertNotIn("\u2019", item["title"])
                seen[url] += 1
        for url, (want, n) in expected.items():
            self.assertEqual(seen[url], n, want)

    def test_generic_culture_cites(self):
        expected = {
            "https://hbr.org/2002/07/make-your-values-mean-something":
                "Make Your Values Mean Something, Patrick M. Lencioni",
            "https://www.jimcollins.com/article_topics/articles/aligning-action.html":
                "Aligning Action and Values, Jim Collins",
            "https://www.jobs.netflix.com/culture":
                "Netflix Culture Memo",
            "https://review.firstround.com/run-this-diagnostic-to-thoughtfully-build-and-evaluate-your-startups-culture/":
                "Run This Diagnostic to Thoughtfully Build (and Evaluate) Your Startup's Culture",
            "https://sloanreview.mit.edu/article/10-things-your-corporate-culture-needs-to-get-right/":
                "10 Things Your Corporate Culture Needs to Get Right, Donald Sull and Charles Sull",
        }
        seen = {url: 0 for url in expected}
        for name, items in lists("generic"):
            for item in items or []:
                url = item["url"]
                if url not in expected:
                    continue
                with self.subTest(file=name, url=url):
                    self.assertEqual(item["title"], expected[url])
                    self.assertNotIn("\u2014", item["note"])
                    self.assertNotIn("DEI", item["note"])
                    self.assertNotIn("DEI", item["title"])
                seen[url] += 1
        for url, title in expected.items():
            self.assertEqual(seen[url], 2, title)

    def test_company_set_cites(self):
        # Official set pages. Titles name the work, and the source when the
        # heading is only a short label. Every URL on a company set other
        # than Amazon and the universal set must be in this list.
        expected = {
            "https://careers.arm.com/life-at-arm":
                "Life at Arm",
            "https://www.arm.com/company":
                "Arm Company",
            "https://www.coupang.jobs/en/coupang-leadership-principles/":
                "Coupang Leadership Principles",
            "https://careers.deliveryhero.com/delivery-hero/2025-4/launching-our-leadership-principles":
                "Launching Our Leadership Principles, Delivery Hero",
            "https://careers.deliveryhero.com/":
                "Delivery Hero Careers",
            "https://handbook.gitlab.com/handbook/values/":
                "GitLab Values",
            "https://handbook.gitlab.com/handbook/values/#collaboration":
                "Collaboration, GitLab Values",
            "https://handbook.gitlab.com/handbook/values/#results":
                "Results for Customers, GitLab Values",
            "https://handbook.gitlab.com/handbook/values/#efficiency":
                "Efficiency, GitLab Values",
            "https://handbook.gitlab.com/handbook/values/#diversity-inclusion":
                "Diversity, Inclusion & Belonging, GitLab Values",
            "https://handbook.gitlab.com/handbook/values/#iteration":
                "Iteration, GitLab Values",
            "https://handbook.gitlab.com/handbook/values/#transparency":
                "Transparency, GitLab Values",
            "https://www.dawnaerospace.com/about":
                "About Dawn Aerospace",
            "https://www.dawnaerospace.com/careers":
                "Careers at Dawn Aerospace",
            "https://www.toyota-global.com/company/history_of_toyota/75years/data/conditions/philosophy/toyotaway2001.html":
                "Toyota Way 2001",
            "https://www.toyota-global.com/pages/contents/investors/ir_library/annual/pdf/2018/ar18_3_en.pdf":
                "Toyota Annual Report 2018, the Toyota Way keywords",
            "https://www.toyota-global.com/company/history_of_toyota/75years/data/conditions/philosophy/index.html":
                "Toyota Corporate Philosophy",
            "https://www.blueorigin.com/careers/work-culture":
                "Blue Origin Work Culture",
            "https://www.blueorigin.com/about-blue":
                "About Blue Origin",
            "https://www.mcjrotc.marines.mil/About/Leadership-Traits/":
                "Leadership Traits",
            "https://www.trngcmd.marines.mil/Portals/207/Site%20Images/TBS/B1X0099XQ%20Officership%20Foundations.pdf":
                "Officership Foundations, The Basic School",
            "https://www.marines.mil/News/Publications/MCPEL/Electronic-Library-Display/Article/899578/mcwp-6-10/":
                "MCWP 6-10 Leading Marines",
            "https://www.marines.mil/News/Publications/MCPEL/Electronic-Library-Display/Article/898678/mcdp-6/":
                "MCDP 6 Command and Control",
            "https://www.smmc.marines.mil/Leading-Marines/":
                "Leading Marines, Sergeant Major of the Marine Corps",
            "https://www.usmcu.edu/LLI":
                "Lejeune Leadership Institute, Marine Corps University",
            "https://www.usmcu.edu/Academic-Programs/Lejeune-Leadership-Institute/Marine-Leader-Development/":
                "Marine Leader Development, Marine Corps University",
            "https://grc-usmcu.libguides.com/cmc-reading-list":
                "Commandant's Professional Reading List",
            "https://www.usmcu.edu/Academic-Programs/Lejeune-Leadership-Institute/LLI-Professional-Reading-List/":
                "Commandant's Professional Reading List, Lejeune Leadership Institute",
        }
        seen = {url: 0 for url in expected}
        for name, items in lists():
            if name.split("/", 1)[0] in ("amazon", "generic"):
                continue
            for item in items or []:
                url = item["url"]
                with self.subTest(file=name, url=url):
                    self.assertIn(url, expected, "unexpected official URL")
                    self.assertEqual(item["title"], expected[url])
                    self.assertNotIn("\u2014", item["note"])
                seen[url] += 1
        for url, title in expected.items():
            self.assertGreater(seen[url], 0, title)

    def test_no_duplicate_urls_in_a_list(self):
        for name, items in lists():
            urls = [i["url"] for i in items or []]
            with self.subTest(file=name):
                self.assertEqual(len(urls), len(set(urls)))


if __name__ == "__main__":
    unittest.main()
