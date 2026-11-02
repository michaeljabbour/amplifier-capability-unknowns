"""Deterministic operations on .ai/unknowns-map.dot.

This module is the SINGLE Python home for the map's deterministic logic:
parsing, quadrant counts, triage precedence, seeding, node add/reclassify,
and the plain-language terminal briefing render (per
unknowns:context/ascii-render-spec.md).

The zero-dependency shell mirror ``scripts/dominant_quadrant.sh`` implements
the SAME triage precedence for environments without this package installed
(the pipeline's parallelogram guard shells it). ``tests/test_triage_contract.py``
asserts the two never drift.

Quadrant codes (see unknowns:context/unknowns-matrix.md):
    kk = known knowns      ku = known unknowns
    uk = unknown knowns    uu = unknown unknowns
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import textwrap as _textwrap
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ._assets import map_template

DEFAULT_MAP = Path(".ai/unknowns-map.dot")

QUADRANTS = ("kk", "ku", "uk", "uu")
QUADRANT_TITLES = {
    "kk": "KNOWN KNOWNS",
    "ku": "KNOWN UNKNOWNS",
    "uk": "UNKNOWN KNOWNS",
    "uu": "UNKNOWN UNKNOWNS",
}

_SEVERITY_ORDER = {"high": 0, "med": 1, "low": 2, None: 3}
_DOT_KEYWORDS = {"graph", "node", "edge", "subgraph", "digraph"}

_LABEL_RE = re.compile(r'label="((?:\\.|[^"\\])*)"')
_NODE_ID_RE = re.compile(r"^\s*([A-Za-z_]\w*)\s*\[")
_UNSUPPORTED_DESC_RE = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\u2028\u2029\ud800-\udfff]"
)
_DESC_ESCAPES = {"\\": "\\", '"': '"', "n": "\n", "r": "\r"}


@dataclass
class Unknown:
    """One node parsed from the map."""

    node_id: str
    desc: str
    quadrant: str | None
    status: str | None
    severity: str | None
    line_no: int  # 0-based index into the file's lines


def _parse_label_attrs(label: str) -> tuple[str, str | None, str | None, str | None]:
    # Only the final metadata separator is structural; earlier escaped line
    # breaks (or literal backslash-n text) belong to the description.
    desc, separator, attrs = label.rpartition("\\n[")
    if not separator:
        desc, attrs = label, label  # tolerate legacy labels without a separator
    desc = re.sub(r'\\([\\"nr])', lambda m: _DESC_ESCAPES[m.group(1)], desc)
    q = re.search(r"quadrant=(\w+)", attrs)
    s = re.search(r"status=(\w+)", attrs)
    sev = re.search(r"severity=(\w+)", attrs)
    return (
        desc,
        q.group(1) if q else None,
        s.group(1) if s else None,
        sev.group(1) if sev else None,
    )


def parse_map(map_path: Path | str = DEFAULT_MAP) -> list[Unknown]:
    """Parse map nodes line-oriented (matches the shell mirror's assumptions:
    quadrant=/status=/severity= live on the same physical label line)."""
    path = Path(map_path)
    if not path.exists():
        return []
    nodes: list[Unknown] = []
    for i, line in enumerate(path.read_text().splitlines()):
        if "->" in line:
            continue  # edge line
        m = _NODE_ID_RE.match(line)
        if not m or m.group(1) in _DOT_KEYWORDS:
            continue
        lm = _LABEL_RE.search(line)
        if not lm or "quadrant=" not in lm.group(1):
            continue
        desc, quadrant, status, severity = _parse_label_attrs(lm.group(1))
        nodes.append(Unknown(m.group(1), desc, quadrant, status, severity, i))
    return nodes


def quadrant_counts(nodes: list[Unknown]) -> dict[str, dict[str, int]]:
    """Per-quadrant open/total counts plus open-high counts."""
    counts = {q: {"open": 0, "total": 0, "open_high": 0} for q in QUADRANTS}
    for n in nodes:
        if n.quadrant not in counts:
            continue
        counts[n.quadrant]["total"] += 1
        if n.status == "open":
            counts[n.quadrant]["open"] += 1
            if n.severity == "high":
                counts[n.quadrant]["open_high"] += 1
    return counts


def dominant_quadrant(map_path: Path | str = DEFAULT_MAP) -> str:
    """Triage routing token: uu | uk | ku | clear.

    EXACT precedence of scripts/dominant_quadrant.sh (first match wins):
      1. any high-severity open unknown-unknown             -> uu
      2. uu open > 0 and >= both uk-open and ku-open        -> uu
      3. uk open > 0 and >= ku open                         -> uk
      4. ku open > 0                                        -> ku
      5. otherwise (including missing map)                  -> clear
    """
    path = Path(map_path)
    if not path.exists():
        return "clear"  # nothing to triage yet; cartography creates the map
    c = quadrant_counts(parse_map(path))
    uu, uk, ku = c["uu"]["open"], c["uk"]["open"], c["ku"]["open"]
    if c["uu"]["open_high"] > 0:
        return "uu"
    if uu > 0 and uu >= uk and uu >= ku:
        return "uu"
    if uk > 0 and uk >= ku:
        return "uk"
    if ku > 0:
        return "ku"
    return "clear"


# ---------------------------------------------------------------------------
# Seeding and mutation
# ---------------------------------------------------------------------------


def seed_map(
    map_path: Path | str = DEFAULT_MAP, task: str = "", force: bool = False
) -> Path:
    """Seed a fresh map from the bundled template. Refuses to overwrite
    an existing map unless ``force`` -- the map is a living artifact."""
    path = Path(map_path)
    if path.exists() and not force:
        raise FileExistsError(f"{path} already exists (pass force=True to overwrite)")
    content = map_template().read_text()
    if task:
        content = content.replace("<describe the task here>", task.replace('"', "'"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def _cluster_span(lines: list[str], quadrant: str) -> tuple[int, int]:
    """(start, end) line indexes of ``subgraph cluster_<q> { ... }``.
    ``end`` is the index of the closing brace line."""
    start = None
    for i, line in enumerate(lines):
        if f"subgraph cluster_{quadrant}" in line:
            start = i
            break
    if start is None:
        raise ValueError(f"cluster_{quadrant} not found in map")
    depth = 0
    for i in range(start, len(lines)):
        depth += lines[i].count("{") - lines[i].count("}")
        if depth == 0 and i > start:
            return start, i
    raise ValueError(f"unbalanced braces in cluster_{quadrant}")


def _node_line(
    node_id: str, desc: str, quadrant: str, status: str, severity: str | None
) -> str:
    attrs = f"quadrant={quadrant}, status={status}"
    if severity:
        attrs += f", severity={severity}"
    # Keep the canonical label on one physical line for both parsers. Reject
    # other controls/line separators and invalid Unicode before any file write.
    unsupported = _UNSUPPORTED_DESC_RE.search(desc)
    if unsupported:
        raise ValueError(
            f"unsupported description character U+{ord(unsupported.group()):04X}"
        )
    desc = (desc.replace("\\", "\\\\").replace('"', '\\"')
            .replace("\n", "\\n").replace("\r", "\\r"))
    extra = ""
    if quadrant == "uu":
        extra = ', fillcolor="#3A3A36", fontcolor="#DDD8CC", color="#777770"'
    elif severity == "high":
        extra = ', color="#C46A4A", penwidth=2'
    return f'    {node_id} [label="{desc}\\n[{attrs}]"{extra}]'


def add_unknown(
    map_path: Path | str,
    quadrant: str,
    desc: str,
    status: str = "open",
    severity: str | None = None,
) -> str:
    """Append a node to a quadrant's cluster. Returns the new node id."""
    if quadrant not in QUADRANTS:
        raise ValueError(f"quadrant must be one of {QUADRANTS}, got {quadrant!r}")
    path = Path(map_path)
    lines = path.read_text().splitlines()
    existing = {n.node_id for n in parse_map(path)}
    n = 1
    while f"{quadrant}_{n}" in existing:
        n += 1
    node_id = f"{quadrant}_{n}"
    _, end = _cluster_span(lines, quadrant)
    lines.insert(end, _node_line(node_id, desc, quadrant, status, severity))
    path.write_text("\n".join(lines) + "\n")
    return node_id


def reclassify(
    map_path: Path | str,
    node_id: str,
    quadrant: str | None = None,
    status: str | None = None,
    severity: str | None = None,
    technique: str = "",
) -> None:
    """Update a node's label attrs; physically move it if the quadrant changes.
    Never deletes -- resolved is a status, not a disappearance."""
    path = Path(map_path)
    lines = path.read_text().splitlines()
    nodes = {n.node_id: n for n in parse_map(path)}
    if node_id not in nodes:
        raise KeyError(f"node {node_id!r} not found in {path}")
    node = nodes[node_id]
    line = lines[node.line_no]
    if quadrant:
        line = re.sub(r"quadrant=\w+", f"quadrant={quadrant}", line)
    if status:
        line = re.sub(r"status=\w+", f"status={status}", line)
    if severity:
        if "severity=" in line:
            line = re.sub(r"severity=\w+", f"severity={severity}", line)
        else:
            line = line.replace(']"', f', severity={severity}]"', 1)
    if technique:
        line = line.rstrip()
        line += f"  // reclassified via {technique}"
    if quadrant and quadrant != node.quadrant:
        del lines[node.line_no]
        _, end = _cluster_span(lines, quadrant)
        lines.insert(end, line)
    else:
        lines[node.line_no] = line
    path.write_text("\n".join(lines) + "\n")


def prune_placeholders(map_path: Path | str) -> int:
    """Remove template placeholder nodes (labels still wrapped in <...>) and
    any edges referencing them. Returns the number of lines removed."""
    path = Path(map_path)
    lines = path.read_text().splitlines()
    placeholder_ids = {
        n.node_id
        for n in parse_map(path)
        if n.desc.startswith("<") and n.desc.endswith(">")
    }
    if not placeholder_ids:
        return 0
    kept: list[str] = []
    removed = 0
    for line in lines:
        tokens = re.findall(r"[A-Za-z_]\w*", line.split("[")[0])
        if any(t in placeholder_ids for t in tokens) and ("[" in line or "->" in line):
            removed += 1
            continue
        kept.append(line)
    path.write_text("\n".join(kept) + "\n")
    return removed


# ---------------------------------------------------------------------------
# Terminal briefing render (unknowns:context/ascii-render-spec.md)
#
# The terminal render is a plain-language BRIEFING, not a grid: the 2x2
# matrix visual belongs to the PNG (`unknowns png`). Rules: wrap, never
# truncate; no quadrant jargon (kk/ku/uk/uu stay internal); every render
# ends with a NEXT step derived from the triage token.
# ---------------------------------------------------------------------------

_WIDTH = 78

_SECTION_TITLES = {
    "ku": "Open questions you know about",
    "uk": "Things you'd recognize but haven't said",
    "uu": "Blindspots surfaced",
}

_NEXT_LINES = {
    "ku": 'Answer the numbered questions under "Open questions" -- '
    'say "interview me" to go one at a time.',
    "uk": "These are preferences you'll recognize on sight but can't describe "
    "yet -- ask for a quick prototype fan-out and react to options.",
    "uu": 'Probe the blindspots before planning -- say "blindspot pass" to dig '
    "into them; a high-severity one can reshape the whole approach.",
    "clear": "No open unknowns -- proceed to planning.",
}


def _task_title(map_path: Path) -> str:
    """Extract the task description from the graph title, if present."""
    try:
        m = re.search(r'task:\s*([^"\\]+)"', map_path.read_text())
        return m.group(1).strip() if m else ""
    except OSError:
        return ""


def _wrap_item(text: str, first_prefix: str) -> list[str]:
    cont = " " * len(first_prefix)
    return _textwrap.wrap(
        text, width=_WIDTH, initial_indent=first_prefix, subsequent_indent=cont
    ) or [first_prefix.rstrip()]


def render_ascii(map_path: Path | str = DEFAULT_MAP) -> str:
    """Plain-language terminal briefing of the map.

    Sections: settled items first, then the three open-unknown sections in
    reading order (known unknowns, unknown knowns, unknown unknowns) with
    continuous numbering, `!!` marking high severity, and a `start here`
    marker on the triage-dominant section. Ends with `NEXT ->`.
    """
    path = Path(map_path)
    nodes = parse_map(path)
    if not nodes:
        return "(no unknowns map found -- seed one with `unknowns seed <task>`)"
    c = quadrant_counts(nodes)
    total = sum(c[q]["total"] for q in QUADRANTS)
    open_n = sum(c[q]["open"] for q in QUADRANTS)
    token = dominant_quadrant(path)

    lines: list[str] = []

    # Header: title left, iceberg progress right.
    title = _task_title(path)
    left = f"UNKNOWNS -- {title}" if title else "UNKNOWNS"
    right = f"{open_n} open / {total} total"
    if len(left) + len(right) + 2 > _WIDTH:
        lines.append(left)
        lines.append(right.rjust(_WIDTH))
    else:
        lines.append(left + " " * (_WIDTH - len(left) - len(right)) + right)

    # Settled: known knowns plus anything already resolved.
    settled_kk = [n for n in nodes if n.quadrant == "kk" and n.status != "open"]
    resolved = [n for n in nodes if n.quadrant != "kk" and n.status == "resolved"]
    lines.append("")
    lines.append("Settled (what you've told me, plus anything already resolved)")
    if not settled_kk and not resolved:
        lines.append("  (nothing yet)")
    for n in settled_kk[:6]:
        lines.extend(_wrap_item(n.desc, "  * "))
    for n in resolved[:6]:
        lines.extend(_wrap_item(n.desc + " (resolved)", "  + "))
    hidden = max(0, len(settled_kk) - 6) + max(0, len(resolved) - 6)
    if hidden:
        lines.append(f"  ... and {hidden} more")

    # Open sections with continuous numbering.
    num = 1
    for q in ("ku", "uk", "uu"):
        open_items = [n for n in nodes if n.quadrant == q and n.status == "open"]
        open_items.sort(key=lambda n: _SEVERITY_ORDER.get(n.severity, 3))
        header = f"{_SECTION_TITLES[q]} ({len(open_items)})"
        if token == q and open_items:
            header += "   <- start here"
        lines.append("")
        lines.append(header)
        if not open_items:
            lines.append("  (none)")
        for n in open_items:
            mark = "!!" if n.severity == "high" else "  "
            lines.extend(_wrap_item(n.desc, f" {mark} {num}. "))
            num += 1

    lines.append("")
    lines.extend(_wrap_item(_NEXT_LINES[token], "NEXT -> "))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Pretty presentation render -- DATA vs PRESENTATION split.
#
# Everything above this line owns the canonical machine format of
# .ai/unknowns-map.dot and is untouched by what follows. The functions below
# only ever READ the canonical map (via parse_map / quadrant_counts) and
# produce a NEW, presentation-only DOT string -- a portrait 2x2 grid with
# plain-language titles, a severity color ramp, and a legend. render_png
# ALWAYS renders through render_pretty_dot; the canonical file is never
# written to by anything in this section.
# ---------------------------------------------------------------------------

_PRETTY_WRAP_WIDTH = 38
_PRETTY_WRAP_MAX_LINES = 4

_SETTLED_FILL, _SETTLED_BORDER = "#DCE9DA", "#6B8E63"
_OPEN_FILL, _OPEN_BORDER = "#FBF1DA", "#C9A55C"
_HIGH_FILL, _HIGH_BORDER = "#F5DDA6", "#A87A1F"
_CRIT_FILL, _CRIT_BORDER = "#EC9A79", "#A63A1C"
_ACCEPTED_RISK_BORDER = "#B5552D"

_CLUSTER_TITLES = {
    "settled": "WHAT WE KNOW FOR SURE",
    "open": "QUESTIONS WE'RE WORKING ON",
    "recognize": "THINGS YOU'D RECOGNIZE ON SIGHT",
    "blindspots": "BLINDSPOTS WE FOUND",
}

_EDGE_LINE_RE = re.compile(r"^\s*(\w+)\s*->\s*(\w+)\s*(?:\[(.*)\])?\s*$")


def _severity_tier(severity: str | None) -> int:
    """critical=0, high=1, everything else (med/low/None)=2."""
    if severity == "critical":
        return 0
    if severity == "high":
        return 1
    return 2


def _pretty_wrap(
    text: str, width: int = _PRETTY_WRAP_WIDTH, max_lines: int = _PRETTY_WRAP_MAX_LINES
) -> str:
    """Word-wrap for a display label; ellipsize rather than overflow.

    Normalizes any literal DOT line-break escape (``\\n``, two characters --
    e.g. from a hand-written multi-line edge label) to a plain space FIRST,
    so re-wrapping recomputes clean breaks instead of corrupting the escape
    when backslashes are sanitized on the next line.
    """
    safe = text.replace("\\n", " ")
    safe = safe.replace('"', "'").replace("\\", "/")
    wrapped = _textwrap.wrap(safe, width=width) or [safe]
    if len(wrapped) > max_lines:
        wrapped = wrapped[:max_lines]
        last = wrapped[-1].rstrip()
        if len(last) >= width:
            last = last[: width - 1].rstrip()
        wrapped[-1] = last + "\u2026"
    return "\\n".join(wrapped)


def _is_accepted_risk(line: str) -> bool:
    return "accepted_risk" in line


def _node_style(n: Unknown, accepted_risk: bool) -> tuple[str, str, float | None]:
    """(fillcolor, bordercolor, penwidth|None) for one node."""
    if accepted_risk:
        return _SETTLED_FILL, _ACCEPTED_RISK_BORDER, 2.0
    if n.status != "open":
        return _SETTLED_FILL, _SETTLED_BORDER, None
    tier = _severity_tier(n.severity)
    if tier == 0:
        return _CRIT_FILL, _CRIT_BORDER, 3.0
    if tier == 1:
        return _HIGH_FILL, _HIGH_BORDER, 1.5
    return _OPEN_FILL, _OPEN_BORDER, None


def _pretty_node_decl(n: Unknown, accepted_risk: bool) -> str:
    fill, border, penwidth = _node_style(n, accepted_risk)
    attrs = f'label="{_pretty_wrap(n.desc)}", fillcolor="{fill}", color="{border}"'
    if penwidth:
        attrs += f", penwidth={penwidth}"
    return f"    {n.node_id} [{attrs}]"


def _sorted_by_tier(items: list[Unknown]) -> list[Unknown]:
    """Critical first, then high, then normal -- stable, so file order is
    preserved within a tier."""
    return sorted(items, key=lambda n: _severity_tier(n.severity))


def _chain(ids: list[str]) -> str | None:
    if len(ids) < 2:
        return None
    return "  " + " -> ".join(ids) + " [style=invis, weight=100]"


def _stitch(a: list[str], b: list[str]) -> str | None:
    if not a or not b:
        return None
    return f"  {a[-1]} -> {b[0]} [style=invis, weight=100]"


def _parse_real_edges(
    lines: list[str], node_ids: set[str]
) -> list[tuple[str, str, str | None]]:
    """Non-invis edges between charted nodes in the CANONICAL file -- hand-added
    reclassification/dependency edges. Carried into the pretty render as
    dashed, non-constraining edges. Skips comments and anything referencing a
    node id this map doesn't chart (e.g. an already-pruned placeholder)."""
    edges: list[tuple[str, str, str | None]] = []
    for line in lines:
        stripped = line.strip()
        if "->" not in stripped or stripped.startswith("//"):
            continue
        m = _EDGE_LINE_RE.match(line)
        if not m:
            continue
        src, dst, attrs = m.group(1), m.group(2), m.group(3) or ""
        if "style=invis" in attrs.replace(" ", ""):
            continue
        if src not in node_ids or dst not in node_ids:
            continue
        lm = re.search(r'label="([^"]*)"', attrs)
        edges.append((src, dst, lm.group(1) if lm else None))
    return edges


def render_pretty_dot(map_path: Path | str = DEFAULT_MAP) -> str:
    """Generate a beautiful, presentation-only DOT from the canonical map.

    Reads .ai/unknowns-map.dot via the existing parse helpers (parse_map,
    quadrant_counts) and NEVER writes to it. Every render (`unknowns png` /
    render_png) goes through this function so every PNG this bundle produces
    is a portrait 2x2 grid with plain-language titles, a severity color ramp,
    and a legend -- never the raw machine DOT.

    Layout: four display clusters (settled / open questions / recognize-on-
    sight / blindspots) plus a legend, arranged as two invisible-spine columns
    so graphviz lays it out as a readable portrait grid without `rankdir`.
    """
    path = Path(map_path)
    raw_lines = path.read_text().splitlines() if path.exists() else []
    nodes = parse_map(path)
    node_ids = {n.node_id for n in nodes}
    accepted: dict[str, bool] = {
        n.node_id: (
            _is_accepted_risk(raw_lines[n.line_no])
            if n.line_no < len(raw_lines)
            else False
        )
        for n in nodes
    }

    settled = _sorted_by_tier([n for n in nodes if n.status != "open"])
    open_ku = _sorted_by_tier(
        [n for n in nodes if n.quadrant == "ku" and n.status == "open"]
    )
    open_uk = _sorted_by_tier(
        [n for n in nodes if n.quadrant == "uk" and n.status == "open"]
    )
    open_uu = _sorted_by_tier(
        [n for n in nodes if n.quadrant == "uu" and n.status == "open"]
    )

    settled_ids = [n.node_id for n in settled]
    open_ids = [n.node_id for n in open_ku]
    recognize_ids = [n.node_id for n in open_uk]
    blindspot_ids = [n.node_id for n in open_uu]

    # Balance the two TOP clusters with invisible spacer nodes so the bottom
    # clusters start on the same rank (per-column layout, forced without
    # rankdir).
    spacer_decls_settled: list[str] = []
    spacer_decls_open: list[str] = []
    spacer_ids_settled: list[str] = []
    spacer_ids_open: list[str] = []
    diff = len(settled_ids) - len(open_ids)
    counter = 1
    if diff > 0:
        for _ in range(diff):
            sid = f"_spacer_{counter}"
            counter += 1
            spacer_ids_open.append(sid)
            spacer_decls_open.append(
                f'    {sid} [style=invis, label="", fixedsize=true, width=0.01, height=0.01]'
            )
    elif diff < 0:
        for _ in range(-diff):
            sid = f"_spacer_{counter}"
            counter += 1
            spacer_ids_settled.append(sid)
            spacer_decls_settled.append(
                f'    {sid} [style=invis, label="", fixedsize=true, width=0.01, height=0.01]'
            )

    settled_col = settled_ids + spacer_ids_settled
    open_col = open_ids + spacer_ids_open

    counts = quadrant_counts(nodes)
    total = sum(counts[q]["total"] for q in QUADRANTS)
    open_n = sum(counts[q]["open"] for q in QUADRANTS)
    title_task = _task_title(path)
    title1 = f"Unknowns map -- {title_task}" if title_task else "Unknowns map"
    title2 = (
        f"Updated {date.today().isoformat()}  |  {open_n} open / {total} charted  |  "
        "most important first in each box"
    )

    out: list[str] = []
    out.append("digraph UnknownsMapPretty {")
    out.append(
        '  graph [bgcolor="#FCFBF8", fontname="Helvetica", fontsize=18,\n'
        '         labelloc=t, fontcolor="#22221F",\n'
        f'         label="{title1}\\n{title2}\\n ",\n'
        "         pad=0.5, nodesep=0.4, ranksep=0.3, compound=true, newrank=true, splines=polyline]"
    )
    out.append(
        '  node  [fontname="Helvetica", fontsize=11, shape=box, style="rounded,filled",\n'
        '         fillcolor="white", color="#55524B", fontcolor="#22221F", width=3.5, margin="0.18,0.11"]'
    )
    out.append('  edge  [fontname="Helvetica", fontsize=9, color="#8A8478"]')
    out.append("")

    out.append("  subgraph cluster_settled {")
    out.append(
        f'    label="{_CLUSTER_TITLES["settled"]}"; fontname="Helvetica-Bold"; fontsize=13'
    )
    out.append(
        '    style="rounded,filled"; fillcolor="#EFF4ED"; color="#9DB396"; margin=14'
    )
    out.append("")
    for n in settled:
        out.append(_pretty_node_decl(n, accepted.get(n.node_id, False)))
    out.extend(spacer_decls_settled)
    out.append("  }")
    out.append("")

    out.append("  subgraph cluster_open {")
    out.append(
        f'    label="{_CLUSTER_TITLES["open"]}"; fontname="Helvetica-Bold"; fontsize=13'
    )
    out.append(
        '    style="rounded,filled"; fillcolor="#FAF4E4"; color="#C9A55C"; margin=14'
    )
    out.append("")
    for n in open_ku:
        out.append(_pretty_node_decl(n, accepted.get(n.node_id, False)))
    out.extend(spacer_decls_open)
    out.append("  }")
    out.append("")

    out.append("  subgraph cluster_recognize {")
    out.append(
        f'    label="{_CLUSTER_TITLES["recognize"]}"; fontname="Helvetica-Bold"; fontsize=13'
    )
    out.append(
        '    style="rounded,filled"; fillcolor="#EFF1F4"; color="#9AA3B0"; margin=14'
    )
    out.append("")
    for n in open_uk:
        out.append(_pretty_node_decl(n, accepted.get(n.node_id, False)))
    out.append("  }")
    out.append("")

    out.append("  subgraph cluster_blindspots {")
    out.append(
        f'    label="{_CLUSTER_TITLES["blindspots"]}"; fontname="Helvetica-Bold"; fontsize=13'
    )
    out.append(
        '    style="rounded,filled"; fillcolor="#F6EBE5"; color="#C08A6E"; margin=14'
    )
    out.append("")
    for n in open_uu:
        out.append(_pretty_node_decl(n, accepted.get(n.node_id, False)))
    out.append("  }")
    out.append("")

    out.append("  subgraph cluster_legend {")
    out.append('    label="HOW TO READ THIS"; fontname="Helvetica-Bold"; fontsize=11')
    out.append(
        '    style="rounded,filled"; fillcolor="#F4F2EE"; color="#B9B2A4"; margin=10'
    )
    out.append('    node [fontsize=9, width=1.5, margin="0.08,0.05"]')
    out.append(
        f'    leg_a [label="Settled", fillcolor="{_SETTLED_FILL}", color="{_SETTLED_BORDER}"]'
    )
    out.append(
        f'    leg_b [label="Open question", fillcolor="{_OPEN_FILL}", color="{_OPEN_BORDER}"]'
    )
    out.append(
        f'    leg_c [label="Important", fillcolor="{_HIGH_FILL}", color="{_HIGH_BORDER}", penwidth=1.5]'
    )
    out.append(
        f'    leg_d [label="Critical -- act first", fillcolor="{_CRIT_FILL}", '
        f'color="{_CRIT_BORDER}", penwidth=3]'
    )
    out.append(
        f'    leg_e [label="Accepted risk", fillcolor="{_SETTLED_FILL}", '
        f'color="{_ACCEPTED_RISK_BORDER}", penwidth=2, width=2.1]'
    )
    out.append("  }")
    out.append("")

    out.append("  // ---- column spines (invisible) ----")
    for chain_line in (
        _chain(settled_col),
        _chain(open_col),
        _stitch(settled_col, recognize_ids),
        _stitch(open_col, blindspot_ids),
        _chain(recognize_ids),
        _chain(blindspot_ids),
    ):
        if chain_line:
            out.append(chain_line)

    left_anchor = (
        recognize_ids[-1]
        if recognize_ids
        else (settled_col[-1] if settled_col else None)
    )
    right_anchor = (
        blindspot_ids[-1] if blindspot_ids else (open_col[-1] if open_col else None)
    )
    out.append("")
    out.append("  // ---- legend placement ----")
    if left_anchor:
        out.append(f"  {left_anchor} -> leg_a [style=invis]")
    if right_anchor:
        out.append(f"  {right_anchor} -> leg_d [style=invis]")
    out.append("  { rank=same; leg_a; leg_b; leg_c; leg_d; leg_e }")
    out.append("  leg_a -> leg_b -> leg_c -> leg_d -> leg_e [style=invis]")

    real_edges = _parse_real_edges(raw_lines, node_ids)
    if real_edges:
        out.append("")
        out.append("  // ---- carried-over edges from the canonical map ----")
        sev_by_id = {n.node_id: n.severity for n in nodes}
        for src, dst, label in real_edges:
            crit = sev_by_id.get(src) == "critical" or sev_by_id.get(dst) == "critical"
            color = _CRIT_BORDER if crit else "#8A8478"
            attrs = (
                f'style=dashed, constraint=false, color="{color}", fontcolor="{color}"'
            )
            if label:
                attrs = (
                    f'label="{_pretty_wrap(label, width=26, max_lines=3)}", ' + attrs
                )
            out.append(f"  {src} -> {dst} [{attrs}]")

    out.append("}")
    return "\n".join(out) + "\n"


def render_png(
    map_path: Path | str = DEFAULT_MAP, out_path: Path | None = None
) -> Path:
    """Render the map to PNG via graphviz, ALWAYS through render_pretty_dot.

    Writes the generated presentation DOT to a temp file (the canonical map
    is only ever read, never written), shells out to `dot -Tpng`, and returns
    the output path. Raises RuntimeError with a clean message if graphviz's
    `dot` binary isn't on PATH.
    """
    if shutil.which("dot") is None:
        raise RuntimeError(
            "graphviz `dot` not found on PATH -- install graphviz to render PNGs"
        )
    path = Path(map_path)
    dot_content = render_pretty_dot(path)
    out = Path(out_path) if out_path else path.with_suffix(".png")
    out.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(suffix=".dot")
    tmp_path = Path(tmp_name)
    try:
        with open(fd, "w", encoding="utf-8") as tmp_file:
            tmp_file.write(dot_content)
        subprocess.run(
            ["dot", "-Tpng", str(tmp_path), "-o", str(out)],
            check=True,
            capture_output=True,
        )
    finally:
        tmp_path.unlink(missing_ok=True)
    return out
