# Tests

```
python3 -m unittest discover -s tests
```

No dependencies. CI runs the same command.

## What is here

`test_validate.py` plants one violation per rule and asserts the validator
catches it. `validate.py` is the only thing standing between the schema and a
corpus that has quietly stopped obeying it, and a rule that stops being
enforced does not announce itself. That has happened once: the Arm-only `group`
rule was written down, believed, and unenforced, and a record with an invented
lens passed.

`test_corpus.py` is about the data rather than the validator. It runs the
validator over the real corpus, checks the fixture is intact, and checks two
things about quotations: that no `quoted` row has been edited away from the
fixture, and that no `authored` row has borrowed a company's wording. It also
checks that SCHEMA.md still describes the code, because a contract the code has
moved on from is worse than no contract.

## Why the fixture is duplicated from porridge

`fixtures/dawn-company-tenets.json` is Dawn Aerospace's own under-index,
over-index, and just-right examples for all 15 Company Tenets, written by
Stefan Powell on 2023/06/12.

Calibration examples are porridge's subject. Porridge owns what under indexed,
balanced, and over done look like in practice, and over time its examples will
be generated rather than written, generalized from the human-written originals
across every company. Those originals came from Amazon, and Dawn's are the
second set. Both were written by people.

So why a copy here.

**A core cannot take a test dependency on one of its apps.** Apps depend on the
core, not the reverse. If these tests read from porridge, the core could not be
validated without checking out an app, and a change in an app could turn the
core red.

**The core needs human-written calibration to test itself against.** The schema
claims a principle decomposes into behavior that can be shown under indexed,
balanced, and over done. Dawn's examples are the sharpest available test of
that claim, because a company wrote them without reference to this schema. They
are the reason `words` exists: 11 of Dawn's 45 strings run past the
one-to-three-sentence rule and one runs to eight, which is how we learned that
the rule is an authoring rule and cannot apply to a quotation.

So this is a deliberate copy of a small, stable, finished thing, not a shared
dependency. Fifteen triples written in 2023 by a person who has moved on. It
does not need syncing, and if it ever does, the drift test is what will say so.

The corpus itself is the other half of the reference. All 336 rows in `data/`
were written by people too. What the fixture adds is a set written by a
company, in the company's voice, which is the one thing we cannot produce.

## What is deliberately not here

The generator, the prompt, and the eval that scores generated rows against
these examples. That is [kindel/porridge#3](https://github.com/kindel/porridge/issues/3).
Testing generated prose is the app's business, and a judge-based eval does not
belong in a check that has to be fast, offline, and deterministic.

The two checks here that touch the fixture are neither of those things. They
are integrity checks: a quotation is still the quotation, and our words are
still ours.

## A note for whoever writes the generator

These human rows *are* the source. Amazon authored and Dawn quoted are the
quality bar the model should sound like. They are not a hold-out exam, and
they are not the porridge table. Porridge shows only `words: generated` rows
on the facet, the way BIQ shows generated packs and keeps the question bank
human.

Nothing in this repo can enforce that split. These tests read files; a prompt
is assembled at runtime and never becomes a file. Marking rows `quoted`,
`authored`, and `generated` is what makes the distinction available.
porridge#3 is where the generator must use the human rows as source, write
generated rows onto the facet, and never copy a human row into the app table
or mark generated output as authored.
