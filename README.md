# Unknowns

Find the question that could change your plan.

Watch the [67-second film](https://michaeljabbour.github.io/amplifier-capability-unknowns/#film): a twelve-step plan, one unchecked assumption, and the small test that finds it before anything moves. The example in it is fictional.

For people starting unfamiliar or uncertain work. Unknowns makes assumptions and unanswered questions visible, attaches an evidence basis and helps choose the next useful inquiry instead of growing an endless risk list.

[Explore the site](https://michaeljabbour.github.io/amplifier-capability-unknowns/)

## What you get

- **Separate facts from assumptions.** Mark what is established, what is open and what is only a possible blind spot.
- **Spend inquiry where it matters.** Choose a question whose answer could alter a decision or acceptance test.
- **Keep a map that can change.** Reclassify an entry when evidence arrives, retaining the source and the reason for the change.

## Start here

```sh
git clone https://github.com/michaeljabbour/amplifier-capability-unknowns.git
cd amplifier-capability-unknowns
python3 scripts/capability.py install --dest ~/.agents/skills
```

This installs the portable method and its packaged references into your agent skill folder. If your host uses another folder, pass that path to `--dest`. Start a new session or use your host’s skill refresh so it can discover the installed skill. Optional native tools are installed separately.

Try this first task:

> Use Unknowns to review a fictional export migration plan. Separate established requirements from compatibility assumptions, attach an evidence basis and choose the one unanswered question most likely to change the plan. Keep possible blind spots labeled as hypotheses.

## What you need

- Python 3.11 or later for the portable install helper.
- The portable method and deterministic map operations need no engine or model key.
- The optional native unknowns CLI can seed, add and triage a map; Graphviz is only needed for image export.
- Pipeline execution is separate from map creation and needs its own configured runner.

For the optional native interface, use a project virtual environment:

```sh
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install .
```

## Evidence and limits

Native map/tool tests and an installed no-engine seed/add/triage check passed. A map or routing token does not demonstrate that an inquiry ran or that rework was avoided.

The worked examples on the site are fictional. They illustrate the output and decisions; they are not user results or measured benefit. See [consolidation and runtime boundaries](docs/CONSOLIDATION.md) for retained interfaces and acceptance scope.

---

## Retained source guide

### amplifier-bundle-unknowns

Compare the plan with the available evidence. Keep established constraints,
open questions, unstated preferences and possible blind spots in one map, then
choose an inquiry whose answer could change the next step. A suggested blind
spot remains a hypothesis until evidence supports it. This workflow does not
guarantee complete discovery or avoided rework.

![Example unknowns map](docs/images/map-example.png)

*Illustrative map from the included example. Real maps may leave quadrants empty; classification is a navigation aid, not proof of completeness.*

## The four boxes

The map offers four categories. Use only categories supported by the task;
do not invent an item to fill a box. Revisit established items when their
evidence changes.

| Box | What lives here |
|---|---|
| **Established information** | Evidence-backed facts, user-stated constraints and resolved questions, with their basis retained. |
| **Open questions** | Explicit questions whose answers may change the work (*known unknowns*). |
| **Unstated preferences** | Candidate constraints or preferences to confirm with the owner (*unknown knowns*). |
| **Possible blind spots** | Hypotheses about missing questions, not discovered facts (*unknown unknowns*). The retained renderer labels this category “Blindspots we found”; assess each item against its evidence. |

## Optional Amplifier workflow

The portable method at the top of this page works through an ordinary agent
host. The deterministic `unknowns` CLI installs separately with
`python3 -m pip install .`; its map operations need no Attractor engine or model key.
Run `unknowns --help` for the installed version.

For the complete native Amplifier workflow, the root bundle includes Attractor
and its interactive orchestration. Configure that host and its provider before
using this optional path. Install the root bundle:

```
amplifier bundle add https://github.com/michaeljabbour/amplifier-capability-unknowns
```

Then pick either of the two easiest first runs.

**One-shot survey.** Point it at a goal to propose an initial map, prioritize
consequential questions and suggest a next inquiry. It need not populate every
quadrant and does not establish that all gaps have been found:

```
/unknownfinder Add a new OIDC auth provider to a codebase I don't know well
```

**Ask the cartographer.** In conversation, just ask the map-owner agent to
chart a task for you:

```
Chart the unknowns for: migrate the session store to Postgres
```

The optional native workflow writes `.ai/unknowns-map.dot`. The CLI can render
it with `unknowns png` when Graphviz is installed.

> **Note:** composing this into your own bundle instead of running it
> standalone? Include `behaviors/unknowns.yaml`, not the root bundle -- see
> [`behaviors/unknowns.yaml`](behaviors/unknowns.yaml) for why.

## What a session feels like

- You seed the map with a goal -- one sentence about what you're trying to do.
- The tool replies with a plain-language briefing: what's settled, what's
  open, what it suspects you'll recognize, and what it thinks nobody asked.
- It offers to go deeper -- an interview (one question at a time) or a
  blindspot pass (it explains the area, then proposes assumptions to test).
- As evidence changes, reclassify the relevant entries. The reclassification
  operation retains resolved entries, so the reason for a change can be inspected.
- It ends every turn with one concrete next step, not a dashboard.

A fictional briefing might read like this:

```
Possible blind spot — unverified hypothesis
  * Is there an agreed success test for the pilot?
    Check the project brief before treating this as a missing requirement.

NEXT -> Answer the open questions, or say "interview me" to go one at a time.
```

## Going deeper

Five ways to run the same logic, from most guided to most raw:

- **Lifecycle pipeline** -- an optional pre/during/post definition for a configured Attractor runner and human gates: [`pipelines/unknowns-lifecycle.dot`](pipelines/unknowns-lifecycle.dot).
- **Amplifier Resolve** -- the pipeline registered in the dot-graph picker: [`pipelines/unknowns-lifecycle.resolver.yaml`](pipelines/unknowns-lifecycle.resolver.yaml).
- **Python library** -- deterministic map operations you can import: [`unknowns_map/`](unknowns_map/) (`import unknowns_map`).
- **Agent tool** -- the map operations exposed to agents: [`modules/tool-unknowns/`](modules/tool-unknowns/).
- **CLI** -- for humans and scripts: `unknowns seed`, `unknowns add`, `unknowns status`.

## File tour

| Path | What it is |
|---|---|
| [`agents/unknowns-cartographer.md`](agents/unknowns-cartographer.md) | The agent that owns the map -- seeds it, renders the briefing, updates it. |
| [`agents/unknownfinder.md`](agents/unknownfinder.md) | Optional survey adapter that loads the canonical method. |
| [`skills/unknowns/SKILL.md`](skills/unknowns/SKILL.md) | The one canonical portable method and its references. |
| [`modes/blindspot.md`](modes/blindspot.md) | Optional `/blindspot` adapter to the canonical method. |
| [`modes/unknownfinder.md`](modes/unknownfinder.md) | Optional `/unknownfinder` survey adapter. |
| [`modes/interview.md`](modes/interview.md) | `/interview` -- one question at a time, hardest-first. |
| [`pipelines/unknowns-lifecycle.dot`](pipelines/unknowns-lifecycle.dot) | Optional lifecycle definition; execution requires the configured runner. |
| [`context/map-template.dot`](context/map-template.dot) | Seed template for a fresh map, with the node schema inline. |
| [`unknowns_map/`](unknowns_map/) | Python package: deterministic map ops + the `unknowns` CLI. |

## Composes with

- **[superpowers](https://github.com/microsoft/amplifier-bundle-superpowers)** -- an entry ramp before `/brainstorm` and an exit gate before `/finish`.
- **[stories](https://github.com/microsoft/amplifier-module-stories)** -- turns the post-work pitch and explainer into HTML stories.
- **[attractor](https://github.com/microsoft/amplifier-bundle-attractor)** -- used by the optional root Amplifier bundle and lifecycle pipeline for orchestration and human gates. It is not required by the portable skill or deterministic map library/CLI.

## Credit

Thariq ([@trq212](https://x.com/trq212)), Claude Code @ Anthropic --
["A Field Guide to Fable: Finding Your Unknowns"](https://x.com/trq212/status/2073100352921215386),
published July 3, 2026.

A reference copy of the article and its images is kept locally in `docs/`
(gitignored -- the original content is Thariq's and is not redistributed with
this repo; follow the link above for the published version).

## Repository migration

This repository was renamed from `amplifier-skill-unknowns` to `amplifier-capability-unknowns`. Existing installed method names, bundle aliases and native interfaces stay the same. See the [migration guide](https://michaeljabbour.github.io/migration/) and [repository map](https://michaeljabbour.github.io/migration/mapping.json) for source URL updates.
