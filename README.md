# principles

The core model for leadership principles: what a principle is, the behavior
it decomposes into, and the vocabulary people use to name it.

The core holds the model, the schema, and the code that enforces them. It
holds no user interface and no app experience. An app depends on it without
inheriting anything it did not ask for.

## The model

A **tenet** is a carefully articulated guiding principle for one endeavor. It
takes a stand, it guides a trade-off, and it settles the calls that data
cannot.

A **leadership principle** is a tenet with a particular subject. Its endeavor
is an organization rather than a project or an initiative, and its subject is
human behavior. That is the whole difference, and it is why the sets here are
written as tenets and held to the same bar.

A principle is only worth having when it decomposes into **behavior**:
something a person can observe, teach, practice, and live with the appropriate
balance. Everything below exists to carry that decomposition.

**Calibration** is how behavior becomes observable. Each behavior is described
in a real situation at three settings: under indexing, getting the balance
right, and over doing it. The two ends are what make a principle teachable
instead of inspirational, and they are the reason a set of abstract nouns
cannot be modeled here. Integrity has no over.

**Facets** are the granular pieces that compose. Companies publish their
principles freely, but they carve the same behavior into different principles
and give them different names, so two companies' sets rarely line up one to
one. A facet names one slice of behavior and points at the calibration it
covers, which is what lets differently named principles meet at the behavior
underneath.

**Terms** are the vocabulary. An alias is the short form used inside a company,
an equivalent is how everyone else says the whole principle, and a facet is how
everyone else says one slice of it. The distinction is the point: asking for an
equivalent returns the whole principle, and asking for a facet returns only the
calibration it covers.

**Level and role** are the dimensions. The same behavior carries a different bar
at junior, senior, and exec, and a different emphasis for an IC, a manager, an
engineer, a PM, and a PGM. The behavior is written once and projected, so that
two tools reading the same behavior at the same level agree.

### Where the schema is today

The model above is the target. The schema implements part of it, and the gaps
are tracked rather than implied:

- Facets are scoped to one principle in one company and cannot yet compose
  across companies, so the shared behavior underneath two companies' sets is
  not expressed.
- Level and role are not in the schema. Apps carry their own notions today.
- The core ships validation and manifest generation. Resolution and projection
  live nowhere yet.

## Tenets

1. **A Principle is a Tenet About People.** A leadership principle is a tenet whose endeavor is an organization and whose subject is human behavior, so *we hold it to the tenet bar*: one idea, a stand, and a trade-off a person can act on. A set that reads as slogans is a set we have not finished modeling.

2. **Behavior is the Unit.** A principle earns its place by decomposing into behavior a person can observe, teach, and live with the appropriate balance. *A behavior we cannot show under indexed, balanced, and over done is a slogan*, and we model it or drop it.

3. **Facets Compose, Wordings Differ.** Companies carve the same behavior into different principles, so their sets rarely line up one to one. *The facet is the granular piece that does line up*, and we compose principles from facets rather than re-authoring one behavior per company.

4. **Level and Role Set the Bar, Not the Behavior.** Junior, senior, and exec differ in the bar for one behavior, and so do an IC, a manager, an engineer, a PM, and a PGM. *The behavior is written once and projected*, because a tool that keeps its own copy per level cannot be compared with the tool beside it.

5. **The Core Owns the Model, Apps Own the Experience.** The core holds the lexicon, the taxonomy, the composition rules, and the code that enforces them. Apps hold questions, prompts, manuals, and pages, and *an app that reimplements the model has forked it*.

6. **Company is a Parameter, Never a Constant.** No code branches on a company's name, and *every lookup, path, and cache key carries the company*. A bare id fails silently, because `dive-deep` is three different principles.

7. **The Company's Own Words, or Nothing.** A set arrives transcribed from the company's own published page, and leaves when that page goes. *A secondhand summary is not evidence*, however confident it reads.

8. **The Check is the Contract.** *A new rule ships with the check that fails on it*, or it is a suggestion. A rule only a human enforces is already broken somewhere in the tree.

9. **Break in the Open.** The core changes shape when the model demands it, and apps follow. *A breaking change ships with the issues and pull requests that fix each app*, so we accept the breakage and never the silence.

10. **A Copy is Generated and Verified, or It Does Not Exist.** An app that must serve the model from its own origin generates its copy from a pin and fails its build on drift. *A copy a human keeps in step is drift with a delay.*

Unless you know better ones.

## The sets

An app picks a company and shows only that company's set. The sets today are
Amazon's Leadership Principles, Arm's 10x Mindset, the Leadership Principles of
Coupang and Delivery Hero, and GitLab's CREDIT values.

Every set is transcribed from the company's own published page. A set the
company no longer publishes does not belong here.

## Layout

```
data/index.json              manifest, generated, version 2
data/amazon/<id>.json        one Amazon principle
data/arm/<id>.json           one Arm factor
data/coupang/<id>.json       one Coupang principle
data/delivery-hero/<id>.json one Delivery Hero principle
data/gitlab/<id>.json        one GitLab value
scripts/build_index.py       regenerates the manifest
scripts/validate.py          enforces SCHEMA.md
SCHEMA.md                    the contract
```

## Use it

Hugo sites mount it as a module:

```
module github.com/kindel/principles
```

An app that serves the model to a browser from its own origin generates a
pinned copy into its own tree and fails its build when the copy no longer
matches the pin.

## Check it

```
python3 scripts/build_index.py
python3 scripts/validate.py
```

Run this before committing. It fails on a stale manifest, a duplicate term
id inside a company, a facet pointing at a row that does not exist, and
every other rule SCHEMA.md states.

## Apps

- `kindel/biq`, behavioral interview questions per principle. Owns the
  questions and the example generator prompt.
- `kindel/porridge`, the user's manual. Owns what under indexed, balanced, and
  over done look like in practice.

There is no kindel/lps repo.
