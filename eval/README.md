# Eval

Held-out calibration, and the guard that keeps it held out.

Authoring `rows` is the expensive part of adding a set. Every candidate in the
queue needs five to 12 situations per principle, each written three times. That
is the obvious thing to generate.

Before generating it, we need a way to tell whether the output is any good.

## The fixture

`golden/dawn-company-tenets.json` is Dawn Aerospace's own under-index,
over-index, and just-right examples for all 15 of its Company Tenets, written
by Stefan Powell on 2023/06/12, years before this repository existed.

That makes it the thing an eval usually cannot get: calibration written by
someone who was not building the generator and was not trying to score well on
it. It is not a sample of our house style. It is an independent answer to the
same question.

Each entry carries the tenet's `name` and verbatim `definition`, which is what
a generator gets as input, and `expected`, which is what Dawn wrote. Dawn's
table gives one triple per tenet with no situation label, so there is no
`situation` field. `traps` names the four entries worth watching.

## The rule

**Golden text does not appear in an authored row.**

A generator reads the corpus for examples. Whatever it may read is its input,
and its input cannot also be its exam.

The hold-out is not "keep Dawn's rows out of `data/`". Dawn's calibration is
going into `data/dawn/` when #14 lands, and it should: it is the best writing
in the corpus and people should be able to read it. It goes in marked
`words: "quoted"`, and the contract on a generator is that it skips every
quoted row. Provenance per row is what makes that possible, and it is the
reason the hold-out survives the set being published.

`check_holdout.py` enforces two things:

- **No leak.** No golden string overlaps an authored row on eight-word
  shingles, which catches the copy and the light paraphrase.
- **No drift.** A quoted row must match the fixture exactly where a fixture
  covers the same principle. A mismatch means a quotation was edited, or one of
  the two transcriptions is wrong.

```
python3 eval/check_holdout.py
```

Two of Dawn's strings are shorter than eight words -- "Analysis paralysis" and
"We are punctual and prepared for meetings." -- and cannot be fingerprinted.
The check names them rather than passing over them. "Analysis paralysis" is
already in three Amazon rows written long before Dawn was on the list, which is
a fair demonstration that a two-word idiom proves nothing.

Neither check can see a prompt. Paste Dawn's rows into a generator as few-shot
examples and nothing here will notice, and the eval is dead. If Dawn's voice is
wanted in a prompt, split the set: some tenets seed, the rest score, and never
mix.

## Scoring

Prose cannot be diffed. Give the generator only the name and the verbatim
definition, ask for under, justRight, and over, and compare against Dawn's.
Cheapest first:

1. **Discrimination.** Show a judge both triples unlabelled and ask which a
   human wrote. If it cannot tell above chance, that is a strong result and a
   cheap one.
2. **Same failure mode.** Does the generated `over` describe the same failure
   as Dawn's? This is the one that matters. The specific authoring error
   `SCHEMA.md` warns about is an `over` that describes a *different* failure
   rather than too much of the same behavior.
3. **Polarity.** Scrappy, not crappy inverts the usual direction: perfectionism
   is its *under*. A generator that has learned "under means not trying" gets
   it backwards, and this is the only set that will tell you.
4. **Concreteness.** Dawn names situations, tools, and a real SpaceX incident
   with a citation. "Does not communicate effectively" fails against "We always
   arrive 10 min late to meetings."

Report per tenet. Fifteen is small enough to read.

Tracked in #25.
