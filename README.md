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
cannot be modeled here.

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

**Level and role** are the dimensions, and they do not move calibration. What
under indexed and over done look like for a behavior is the same for a junior
and for an exec: not checking the number yourself is the same failure at every
level, and so is rebuilding every number and never deciding. What moves is
which behaviors carry weight, and the scope at which they are expected. Where a
particular behavior genuinely does read differently by level, that is a
property of that behavior rather than a rule about level, so it is stated on
the behavior and not applied across the board. The behavior is written once and
projected, so that two apps reading the same behavior at the same level
agree. Level and role also scope whole sets, not only behaviors within one: a
set can apply to one role at one level and layer on the set beneath it.

### Where the schema is today

The model above is the target. The schema implements part of it, and the gaps
are tracked rather than implied:

- The cross-company facet map (`data/facets.json`) expresses the shared behavior
  underneath two companies' sets. Same facet, same generated examples in the
  app. Human rows on records are source for the generator, not the porridge
  table.
- Level and role are not in the schema. Apps carry their own notions today.
  Calibration is level-independent, so this is an additive selection and
  weighting layer rather than a change to `rows`.
- A company has one set. Amazon publishes at least two, the Leadership
  Principles and the Principal Engineering Community Tenets, and the second
  layers on the first for engineers at principal and above. A set scoped to a
  role and a level, or layered on another set, cannot be expressed.
- The core ships validation and manifest generation. Resolution and projection
  live nowhere yet.

## Tenets

1. **A Principle is a Tenet About People.** A leadership principle is a tenet whose endeavor is an organization and whose subject is human behavior, so *we hold it to the tenet bar*: one idea, a stand, and a trade-off a person can act on. A set that reads as slogans is a set we have not finished modeling.

2. **Behavior is the Unit.** A principle earns its place by decomposing into behavior a person can observe, teach, and live with the appropriate balance. *A behavior we cannot show under indexed, balanced, and over done is a slogan*, and we model it or drop it.

3. **Facets Compose, Wordings Differ.** Companies carve the same behavior into different principles, so their sets rarely line up one to one. *The facet is the granular piece that does line up*, and we compose principles from facets rather than re-authoring one behavior per company.

4. **Level and Role Change What Counts, Not What Good Looks Like.** Over doing it looks the same for a junior and an exec, so calibration does not move with level or role. What moves is which behaviors carry weight and the scope expected, and *the behavior is written once and projected*, because an app that keeps its own copy per level cannot be compared with the app beside it.

5. **The Core Owns the Model, Apps Own the Experience.** The core holds the lexicon, the taxonomy, the composition rules, and the code that enforces them. Apps hold questions, prompts, manuals, and pages, and *an app that reimplements the model has forked it*.

6. **Company is a Parameter, Never a Constant.** No code branches on a company's name, and *every lookup, path, and cache key carries the company*. A bare id fails silently, because `dive-deep` is three different principles.

7. **The Check is the Contract.** *A new rule ships with the check that fails on it*, or it is a suggestion. A rule only a human enforces is already broken somewhere in the tree.

8. **Break in the Open.** The core changes shape when the model demands it, and apps follow. *A breaking change ships with the issues and pull requests that fix each app*, so we accept the breakage and never the silence.

9. **A Copy is Generated and Verified, or It Does Not Exist.** An app that must serve the model from its own origin generates its copy from a pin and fails its build on drift. *A copy a human keeps in step is drift with a delay.*

Unless you know better ones.

## The sets

An app picks a company and shows only that company's set. The sets today are
Amazon's Leadership Principles, Arm's 10x Mindset, the Leadership Principles of
Coupang and Delivery Hero, GitLab's CREDIT values, Dawn Aerospace's Company
Tenets, and Toyota's The Toyota Way.

Every set is the company's own text, published here with the company's
permission. Usually that is a page the company publishes itself. It can also be
a first-party document the company has authorized us to publish, an internal
handbook or wiki page, named in `source` instead of a URL. What it is never is
somebody else's account of a set, however faithful the reproduction looks.

Where a company has written its own calibration, that is transcribed too and
marked `words: "quoted"`, so the company's words and ours never blur together
inside one record. Rows an app writes are marked `generated` for the same
reason.

## Layout

```
data/index.json              manifest, generated, version 5
data/facets.json             cross-company facet map
data/amazon/<slug>.json        one Amazon principle
data/arm/<slug>.json           one Arm factor
data/coupang/<slug>.json       one Coupang principle
data/delivery-hero/<slug>.json one Delivery Hero principle
data/gitlab/<slug>.json        one GitLab value
data/dawn/<slug>.json          one Dawn Aerospace tenet
data/toyota/<slug>.json        one Toyota Way keyword
scripts/build_index.py       regenerates the manifest
scripts/validate.py          enforces SCHEMA.md
tests/                       what CI runs, and the calibration it checks against
.github/workflows/ci.yml     validate, test, and check the manifest
SCHEMA.md                    the contract
AGENTS.md                    agent ops: adding a company, the consumers
.kindel/consumers.txt        who the cascade pings
```

Generating rows, and judging generated rows, belong in the apps. `tests/` keeps
a copy of the human-written calibration those apps generalize from, and uses it
to check that the model can still express the real thing. See `tests/README.md`.

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

Two apps, plus the site that hosts them. `.kindel/consumers.txt` is the
list the cascade pings. Adding a company here is not finished until both
apps can show it.

- `kindel/porridge` mounts this module and renders the calibration.
- `kindel/biq` keeps a fixed question set. Each question maps to facets.
  A new company inherits those questions (and their generated examples)
  through the facet map, not by writing a second bank.
- `kindel/kindelwww` is the host. A local Hugo preview that only replaces
  this module will show porridge and still miss BIQ.

See `AGENTS.md` for the add-a-company path.

## License

MIT. Copyright (c) 2026 Kindel, LLC. Keep the copyright notice and permission notice in all copies.
