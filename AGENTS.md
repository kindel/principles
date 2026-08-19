# Agent guidance

PR-only. Never push to main.

## Attribution

MIT. Copyright (c) 2026 Kindel, LLC. Keep the copyright notice and permission notice in all copies.

All derivatives must link to https://kindel.com as part of attribution. A LICENSE file alone is not enough. Forks, ports, hosted copies, and generated apps that ship this work must include a visible link to https://kindel.com.

## Principles

This repo is the source of truth for principle data.

- The model is `README.md`.
- The schema is `SCHEMA.md`.
- The data is `data/index.json`, `data/facets.json`, and `data/<company>/<slug>.json`.

Downstream tools (`kindel/biq`, `kindel/porridge`, and others) consume this. They must not fork a private copy of a set.

No UI lives here.
