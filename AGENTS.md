# Working in amplifier-bundle-unknowns

This is an Amplifier **bundle repo** — composition (YAML/markdown/DOT) —
that also ships a real Python package (`unknowns_map`, L2/L4 in the
leverage-levels table below). It has a test suite: run it with `pytest`
from the repo root (`tests/` plus `modules/tool-unknowns/tests/`, wired via
`[tool.pytest.ini_options]` in `pyproject.toml`).

## Validate

- **Tests:** `pytest` from the repo root. `tests/test_map_ops.py` and
  `tests/test_render_pretty.py` cover the deterministic core (parsing,
  mutation, both renderers); `tests/test_triage_contract.py` guards the
  Python/shell triage parity contract.
- **Bundle validity:** run the `validate-bundle-repo` flow from an Amplifier
  session (it checks composition, namespaces, and auto-regenerates a stale
  `bundle.dot`).
- **Conformance:** run `/audit-bundle .` (conformance bundle) before opening
  a PR or after any structural change.
- **Pipeline DOT sanity:** `dot -Tpng pipelines/unknowns-lifecycle.dot -o /tmp/lifecycle.png`
  (Graphviz must parse it cleanly).
- **Shell guard:** `bash scripts/dominant_quadrant.sh` against a sample
  `.ai/unknowns-map.dot` if you touch the triage logic.

## Regenerate docs diagram

`bundle.dot` + `bundle.png` at the repo root follow the bundle-to-dot v3
convention (embedded `source_hash` freshness tracking). Regenerate after
changing `bundle.md`, anything in `behaviors/`, `agents/`, `context/`,
`modes/`, or `skills/`:

```python
from amplifier_foundation.bundle_docs import bundle_repo_dot
open("bundle.dot", "w").write(bundle_repo_dot("."))
```

```bash
dot -Tpng bundle.dot -o bundle.png
```

Note: `.gitignore` excludes `*.png` but explicitly re-includes `bundle.png`.

## Pitfalls

- **Include the modes *behavior*, NOT the full amplifier-bundle-modes bundle**
  in `behaviors/unknowns.yaml` — the full bundle transitively includes
  foundation, which would re-run foundation's includes a second time
  (see the comment at `behaviors/unknowns.yaml:15-19`).
- **`context/unknowns-awareness.md` is propagated via `context.include` in
  `behaviors/unknowns.yaml` only.** Do NOT also `@mention` it from
  `bundle.md` — that duplicates its content in the system prompt of every
  direct user of this bundle.
- **The living map (`.ai/unknowns-map.dot`) is a runtime artifact** — it is
  generated per-task and gitignored. Never commit one.
- **DATA vs PRESENTATION is a hard split.** The canonical map format (parsed
  by `map_ops.parse_map` and mirrored by `scripts/dominant_quadrant.sh`)
  never changes for rendering's sake. `render_pretty_dot` reads the
  canonical map and generates a SEPARATE, presentation-only DOT (plain-
  language cluster titles, portrait 2x2 grid, severity color ramp, legend);
  `render_png` always renders through it. Never shell out to
  `dot -Tpng .ai/unknowns-map.dot` directly — that renders the raw machine
  DOT (jargon cluster names, dual-purpose labels) instead of the beautiful
  presentation every consumer of this bundle expects. Regenerate the
  reference example any time the render logic changes:
  `python scripts/make_example_map.py` writes `docs/images/map-example.png`
  (the one exception to `docs/` being gitignored — see `.gitignore`).
- **`docs/` is gitignored, except `docs/images/`.** `docs/` holds a local
  reference copy of the original article and images (not redistributed);
  don't reference `docs/source` paths from bundle composition files.
  `docs/images/` is the one carved-out exception — it holds versioned
  example renders (e.g. `map-example.png`) referenced by `README.md`.
- **`/blindspot` must remain an inline skill** (it converses with the user);
  do not convert it to a fork skill.
- **`tool-skills` has NO @mention resolution** — a `config.skills:` entry like
  `"@unknowns:skills"` is *silently ignored* (skills sit on disk, never
  materialize, no error anywhere). Use the git self-reference form:
  `git+https://github.com/michaeljabbour/amplifier-capability-unknowns@main#subdirectory=skills`.
  Note the asymmetry: `hooks-mode`'s `search_paths` DOES resolve @mentions —
  the two modules use different code paths. Live-confirmed in a DTU run
  (2026-07-08); a static conformance audit had passed the @mention form.
- **`/unknownfinder` is a thin alias** for the `unknowns:unknownfinder` agent —
  the method lives only in `agents/unknownfinder.md`. Never re-implement the
  procedure in the skill; edit the agent.

## Capability consolidation (2026-10-28)

The canonical method now lives in skills/unknowns/SKILL.md and its references. Legacy slash names are mode adapters; their archived skill text uses REFERENCE.md. The unknownfinder agent loads the packaged method. Preserve the deterministic unknowns_map library, CLI and canonical DOT/pretty-renderer split.

## Market research upkeep

Local-only market research lives in `.research/market/` (gitignored; never commit it).

At session start, check `.research/market/last_updated`:
- If the file is missing, seed it from this repository's README and capability source/provenance links, using cited primary sources and local retrieval dates.
- If it is older than 30 days, or before any positioning, launch or naming work, refresh it with cited primary sources (URL + retrieved date).
- Keep it local. Never commit it and never copy private research into public docs.
- Log every change in `.research/market/CHANGELOG.md`.

## Capability identity

Public capability identity: `amplifier-capability-unknowns`. Preserve the existing portable method folder, native interfaces and legacy installation routes across the approved repository rename.
