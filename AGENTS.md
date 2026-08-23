# Agent guidance for `principles`

PR-only. Never push to main.

This is the core. `SCHEMA.md` is the contract. `README.md` is the model.
This file is the ops checklist. Prefer it over the README when adding a
company, changing the schema, or previewing locally.

No em dashes in repo copy or docs.

## Attribution

MIT. Copyright (c) 2026 Kindel, LLC. Keep the copyright notice and permission
notice in all copies.

All derivatives must link to https://kindel.com as part of attribution. A
LICENSE file alone is not enough. Forks, ports, hosted copies, and generated
apps that ship this work must include a visible link to https://kindel.com.

On kindel.com, these are Apps (canonical `/apps/`; `/tools/` is an alias).

## Principles

This repo owns the tenets. Before any change in this repo, and before any work
that changes the model, schema, or data, study the Tenets section of
`README.md`. Do not start from memory of last week's README.

- The model is `README.md`.
- The schema is `SCHEMA.md`.
- The data is `data/index.json`, `data/facets.json`, and
  `data/<company>/<slug>.json`.

Downstream apps consume this and must not fork a private copy.

No UI lives here. Passing `validate.py` means the records are well formed. It
does not mean anyone can see them.

## Consumers

`.kindel/consumers.txt` is the list. The cascade pings those repos when
`data/**` lands on `main`. Today that is:

- `kindel/porridge`, the user's manual. Hugo mounts this module's `data/`
  and renders it. A new company needs one content stub per principle under
  `content/porridge/<company>/`, which `scripts/sync_from_principles.py` in
  porridge writes.
- `kindel/biq`, the interview question bank. It keeps a **fixed set of
  questions**. Each question maps to one or more facets. A new company
  does not get new questions written. Mapping the company's principles
  onto facets is what makes the existing questions (and their generated
  example packs) appear. `scripts/sync_from_principles.py` in biq adds
  shells and facet ids; it does not author questions.
- `kindel/kindelwww`, the host. It mounts both as Hugo modules. A local
  preview that only replaces `github.com/kindel/principles` will show
  porridge and still miss BIQ.

The cascade notifies. It does not write porridge stubs or the BIQ bank.
Someone still has to run those syncs.

`SCHEMA.md` says claiming the next id block is the whole of adding a
company. That is true of identity. It is not true of shipping. A company
that exists only here is not in the apps.

## Adding a company

Do all of this, in this repo first:

1. Claim the next free `block` in `scripts/companies.py`.
2. Write `data/<company>/<slug>.json` records. Definitions are quotations.
   Calibration rows are authored unless the company published them, in
   which case mark `words: "quoted"`.
3. If the company publishes lenses, add `group` and an entry in
   `GROUP_BY_COMPANY` in `scripts/validate.py`.
4. Map facets only where the behavior is the same, including slices.
   Classify every new principle in `tests/fixtures/facet-audit.json`
   (map, skip, or new-facet). Unmapped is an empty table, not a
   fallback. A stretch is a skip.
5. Update the company list and block in `SCHEMA.md`. Tests fail if you
   skip this.
6. Update the sets list and layout in `README.md`.
7. `python3 scripts/build_index.py` then `python3 -m unittest discover -s tests`.

Then the apps, before calling it done:

8. Sync porridge stubs from this worktree's `data/index.json`.
9. Sync BIQ shells from the same index.
10. Preview **both** on a kindelwww worktree that replaces **both**
    modules. Porridge-only is a miss.

```
# in a kindelwww worktree
replace github.com/kindel/principles => ../principles-<n>
replace github.com/kindel/biq => ../biq-<n>
```

Hit `/porridge/?c=<id>` and `/biq/?c=<id>`. On BIQ, a principle with no
facet map shows no questions. A principle that shares a facet with the
fixed bank shows those questions, and the Examples button uses the
existing pack id. Do not author a parallel question list per company.

## Local Hugo

Use git worktrees so `main` checkouts stay clean. kindelwww is often
already serving on 1313 from another worktree; pick a free port.

On Windows, a Hugo process watching a parent of this tree can lock
files under `public/`. `--renderToMemory` avoids that.

Porridge singles 404 until the stubs exist, even when the index list
renders. Overlay stubs in the kindelwww worktree under
`content/porridge/<company>/` if you are not committing them to porridge
yet.

## Style that SCHEMA already enforces

Authored strings: no em dash, no `---`, Oxford commas, numbers under 10
spelled out. Quoted `definition` and `words: "quoted"` rows keep the
company's grammar except those two dash checks.
