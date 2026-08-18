#!/usr/bin/env python3
"""The catalog of companies, in manifest order.

A record knows its own company id. This adds the public name, the title of
the set, and where the definitions are transcribed from. `source` is a URL when
the company publishes the set itself and the name of the first-party document
when it does not; see Sourcing in SCHEMA.md. It lives here so build_index.py
and validate.py cannot disagree about it.

`block` is the company's reserved range of principle ids, a thousand numbers
starting at the block. A principle id is globally unique, so an app that looks
one up by id alone cannot land on another company's record, which is a bug
every consumer of this repository has shipped at least once. The block makes
the company readable off the number, and claiming the next free block is the
whole of adding a company. Numbers are never reused and never renumbered: a
principle keeps the id it was given even if it is renamed or resorted.
"""

import collections

COMPANY_META = collections.OrderedDict([
    ("amazon", {
        "block": 1000,
        "name": "Amazon",
        "set": "Leadership Principles",
        "source": "https://www.amazon.jobs/content/en/our-workplace/leadership-principles",
    }),
    ("arm", {
        "block": 2000,
        "name": "Arm",
        "set": "10x Mindset",
        "source": "https://careers.arm.com/life-at-arm",
    }),
    ("coupang", {
        "block": 3000,
        "name": "Coupang",
        "set": "Leadership Principles",
        "source": "https://www.coupang.jobs/en/coupang-leadership-principles/",
    }),
    ("delivery-hero", {
        "block": 4000,
        "name": "Delivery Hero",
        "set": "Leadership Principles",
        "source": "https://careers.deliveryhero.com/delivery-hero/2025-4/launching-our-leadership-principles",
    }),
    ("gitlab", {
        "block": 5000,
        "name": "GitLab",
        "set": "CREDIT Values",
        "source": "https://handbook.gitlab.com/handbook/values/",
    }),
    ("dawn", {
        "block": 6000,
        "name": "Dawn Aerospace",
        "set": "Company Tenets",
        # Not on dawnaerospace.com. Dawn's internal wiki, exported to
        # "Dawn Aerospace Company Tenets.docx" and published here with Dawn's
        # permission. See Sourcing in SCHEMA.md.
        "source": "Dawn Aerospace Company Tenets, Dawn's internal wiki, published with Dawn's permission",
    }),
])
