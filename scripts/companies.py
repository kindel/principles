#!/usr/bin/env python3
"""The catalog of companies, in manifest order.

A record knows its own company id. This adds the public name, the title of
the set, and the page the definitions are transcribed from. It lives here so
build_index.py and validate.py cannot disagree about it.
"""

import collections

COMPANY_META = collections.OrderedDict([
    ("amazon", {
        "name": "Amazon",
        "set": "Leadership Principles",
        "source": "https://www.amazon.jobs/content/en/our-workplace/leadership-principles",
    }),
    ("arm", {
        "name": "Arm",
        "set": "10x Mindset",
        "source": "https://careers.arm.com/life-at-arm",
    }),
    ("coupang", {
        "name": "Coupang",
        "set": "Leadership Principles",
        "source": "https://www.coupang.jobs/en/coupang-leadership-principles/",
    }),
    ("delivery-hero", {
        "name": "Delivery Hero",
        "set": "Leadership Principles",
        "source": "https://careers.deliveryhero.com/delivery-hero/2025-4/launching-our-leadership-principles",
    }),
    ("gitlab", {
        "name": "GitLab",
        "set": "CREDIT Values",
        "source": "https://handbook.gitlab.com/handbook/values/",
    }),
])
