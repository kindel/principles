# Agent guidance for `principles`

This is the core. `SCHEMA.md` is the contract. `README.md` is the model.
This file is the ops checklist. Prefer it over the README when adding a
company, changing the schema, or previewing locally.

No em dashes in repo copy or docs.

## What this repo is not

It has no UI. Passing `validate.py` means the records are well formed. It
does not mean anyone can see them.

## Consumers

`.kindel/consumers.txt` is the list. The cascade pings those repos when
`data/**` lands on `main`. Today that is:

- `kindel/porridge`, the user's manual. Hugo mounts this module's `data/`
  and renders it. A new company needs one content stub per principle under
  `content/porridge/<company>/`, which `scripts/sync_from_principles.py` in
  porridge writes.
- `kindel/biq`, the interview question bank. **It does not read this repo
  at runtime.** `data/questions.json` is its own bank. `scripts/sync_from_principles.py`
  in biq adds company and principle shells (empty `questions`,
  `examples: false`). Writing the questions, generating hire/no-hire
  packs, and flipping `examples` to true are later steps in that repo.
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

Hit `/porridge/?c=<id>` and `/biq/?c=<id>`. BIQ shells with zero questions
are expected. The company has to appear in the picker.

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
