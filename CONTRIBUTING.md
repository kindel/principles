# Contributing

A change to the principles starts as a GitHub issue, unless you are opening the pull request yourself.

Use the issue forms:

- Add a company's principles. Name the company. Give the source: a link to the official page where they published them, or the name of a first-party document they have authorized us to publish. Say how you know them if you want.
- Improve an example or a calibration row. Name or link the principle, quote the current text, suggest the better text, and say why.
- Something is wrong or out of date. Say what it is and where it is.

A new facet can be a blank issue. Describe the behavior under, just right, and over.

I, or an agent, turn an issue into a pull request. Say in the issue if you want your name on it.

If you write the change yourself, read [AGENTS.md](AGENTS.md) and [SCHEMA.md](SCHEMA.md). Run `python3 scripts/validate.py` and `python3 -m unittest discover -s tests` before you push. Do not push to main.

Porridge and BIQ have a Give Feedback button. That files an issue on the app's repo, `kindel/porridge` or `kindel/biq`, not in this repo.
