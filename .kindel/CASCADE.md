# Cascade

When this repo's data changes, GitHub Actions pings the apps. The apps open a PR. When any Kindel module lands on its default branch, kindelwww opens a pin PR.

Nothing writes the default branch. Example packs still spend credits only from the existing manual workflow.

## Secret

Add an org (or per-repo) secret named `CASCADE_TOKEN`. A fine-grained PAT or GitHub App token that can:

- send `repository_dispatch` to `kindel/porridge`, `kindel/biq`, and `kindel/kindelwww`
- (if you use one token everywhere) the same for `kindel/tenets`, `kindel/5ps`, and `kindel/dvfr`

Without the secret, notify jobs skip. Same-repo sync and pin jobs still run from `workflow_dispatch`.

## Hops

1. principles `main` (data) → porridge `cascade` and biq `cascade`, plus kindelwww `pin-modules`
2. porridge / biq / tenets / 5ps / dvfr default branch → kindelwww `pin-modules`
3. kindelwww pin job `go get`s every direct `github.com/kindel/*` require and opens `pin/modules`

Porridge writes missing page stubs. BIQ writes missing company and principle shells with `examples: false` and empty questions. It does not invent a bank or generate packs.
