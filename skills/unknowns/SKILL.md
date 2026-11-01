---
name: unknowns
description: "Expose the assumptions and unanswered questions that could change a plan, then choose the next useful inquiry. Use when asked to find blind spots, map uncertainty, or decide what to investigate next."
---

# Unknowns

Map the task against the actual territory: code, records and user constraints. Separate established claims (known knowns), explicit questions (known unknowns), unstated assumptions (unknown knowns) and possible blind spots (unknown unknowns). Do not force every quadrant to contain an item.

Map: read references/unknowns-matrix.md and references/unknownfinder.md. Attach an evidence basis and severity to each consequential item. Possibilities are hypotheses, not discovered facts. Prefer a useful question over a large inventory of speculative hazards.

Blindspot: stay in the current conversation. Surface one assumption or ask one question whose answer could change the plan. Do not delegate away the interaction when the user's answers are the needed evidence.

Resolve: use the retained unknowns CLI and unknowns_map library for deterministic map operations. Seed, add, reclassify, status and triage work without an engine or API key. Keep the canonical machine DOT separate from the pretty renderer. Graphviz is optional for PNG export. Select the next inquiry from the dominant unresolved quadrant and update its status only when evidence changes.

The existing /unknownfinder alias and agents remain optional Amplifier adapters to the same method. Pipeline execution is optional and requires its own configured engine; a rendered map or routing token is not evidence that the inquiry ran. Generated .ai/unknowns-map.dot belongs to the user's task, never to the source release.

## Optional coaching checkpoint

Read [the local coaching guide](references/coaching-session.v1.md) only when the person asks for practice or optional session bookkeeping. Keep direct artifact production available; agree a small budget, preserve the baseline and stop on goal, user exit or no meaningful gain.
