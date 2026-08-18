# Hold out

Company-written calibration, kept clean so that something else can score
against it.

The scoring lives in the app. `kindel/porridge` owns what under indexed,
balanced, and over done look like in practice, so a generator that writes rows
and the eval that judges it both belong there. What belongs here is the data
and the guarantee about it: these words are the company's, they have not been
edited, and nothing that reads this corpus for examples has been shown them.

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
`situation` field. `traps` names the four entries worth watching, which is a
property of Dawn's writing rather than a scoring rule.

The fixture is a snapshot taken before Dawn's set lands in `data/dawn/`. Once
it has landed, the golden rows are the ones marked `words: "quoted"` and a
consumer should read them from there rather than from this file. This file
stays as the anchor the drift check compares against.

## The contract

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
python3 holdout/check_holdout.py
```

Two of Dawn's strings are shorter than eight words -- "Analysis paralysis" and
"We are punctual and prepared for meetings." -- and cannot be fingerprinted.
The check names them rather than passing over them. "Analysis paralysis" is
already in three Amazon rows written long before Dawn was on the list, which is
a fair demonstration that a two-word idiom proves nothing.

Neither check can see a prompt. Paste Dawn's rows into a generator as few-shot
examples and nothing here will notice, and the eval is dead. If Dawn's voice is
wanted in a prompt, split the set: some tenets seed, the rest score, and never
mix. That is a rule for whoever writes the prompt, which is not this
repository.

Tracked in #25. The generator and its eval are tracked in `kindel/porridge`.
