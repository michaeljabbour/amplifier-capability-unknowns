"""Deterministic core tests: seed -> add -> counts -> triage -> mutate -> render."""

from pathlib import Path

import pytest

from unknowns_map import map_ops


@pytest.fixture
def seeded(tmp_path: Path) -> Path:
    m = tmp_path / ".ai" / "unknowns-map.dot"
    map_ops.seed_map(m, task="test the map")
    return m


def test_seed_creates_map_with_task(seeded: Path):
    content = seeded.read_text()
    assert "test the map" in content
    assert "cluster_uu" in content


def test_seed_refuses_overwrite(seeded: Path):
    with pytest.raises(FileExistsError):
        map_ops.seed_map(seeded, task="again")
    map_ops.seed_map(seeded, task="again", force=True)  # force works


def test_add_and_counts(seeded: Path):
    map_ops.prune_placeholders(seeded)
    map_ops.add_unknown(seeded, "kk", "user wants X", status="given")
    map_ops.add_unknown(seeded, "ku", "which session store?", severity="med")
    map_ops.add_unknown(seeded, "ku", "token refresh strategy", severity="high")
    map_ops.add_unknown(seeded, "uu", "legacy SAML users exist")
    c = map_ops.quadrant_counts(map_ops.parse_map(seeded))
    assert c["kk"]["total"] == 1 and c["kk"]["open"] == 0
    assert c["ku"]["open"] == 2
    assert c["uu"]["open"] == 1


@pytest.mark.parametrize(
    "desc",
    [
        "Can export preserve\nall Unicode?",
        "first\rsecond",
        "first\r\nsecond",
        'Keep "quoted text" and C:\\new\\reports\\',
        r"Keep literal \n and \r escapes",
        "Unicode: café Ελληνικά 中文 🧭 e\u0301",
        "  preserve leading and trailing whitespace\t ",
    ],
    ids=["lf", "cr", "crlf", "quotes-backslashes", "literal-escapes", "unicode", "whitespace"],
)
def test_description_roundtrip_and_reclassify(seeded: Path, desc: str):
    map_ops.prune_placeholders(seeded)
    node_id = map_ops.add_unknown(seeded, "ku", desc, severity="med")
    nodes = map_ops.parse_map(seeded)
    assert len(nodes) == 1
    assert (nodes[0].node_id, nodes[0].desc, nodes[0].quadrant, nodes[0].status) == (
        node_id, desc, "ku", "open"
    )
    assert map_ops.dominant_quadrant(seeded) == "ku"
    assert len([line for line in seeded.read_text().splitlines() if f"{node_id} [" in line]) == 1

    # The description survives an in-place update and a physical cluster move.
    map_ops.reclassify(seeded, node_id, severity="high")
    map_ops.reclassify(seeded, node_id, quadrant="uu", status="resolved")
    nodes = map_ops.parse_map(seeded)
    assert len(nodes) == 1
    assert (nodes[0].node_id, nodes[0].desc, nodes[0].quadrant,
            nodes[0].status, nodes[0].severity) == (node_id, desc, "uu", "resolved", "high")
    assert map_ops.dominant_quadrant(seeded) == "clear"


@pytest.mark.parametrize("char", ["\x00", "\v", "\f", "\x1c", "\x85", "\u2028", "\u2029", "\ud800"])
def test_unsupported_description_characters_do_not_mutate(seeded: Path, char: str):
    before = seeded.read_bytes()
    with pytest.raises(ValueError, match="unsupported description character"):
        map_ops.add_unknown(seeded, "ku", f"before{char}after")
    assert seeded.read_bytes() == before


def test_add_to_missing_map_does_not_create_file(tmp_path: Path):
    missing = tmp_path / "missing.dot"
    with pytest.raises(FileNotFoundError):
        map_ops.add_unknown(missing, "ku", "first\nsecond")
    assert not missing.exists()


def test_triage_precedence(tmp_path: Path):
    m = tmp_path / "map.dot"
    map_ops.seed_map(m, task="t")
    map_ops.prune_placeholders(m)
    assert map_ops.dominant_quadrant(m) == "clear"
    # ku only -> ku
    map_ops.add_unknown(m, "ku", "q1")
    assert map_ops.dominant_quadrant(m) == "ku"
    # uk ties ku -> uk wins (uk >= ku)
    map_ops.add_unknown(m, "uk", "pref1")
    assert map_ops.dominant_quadrant(m) == "uk"
    # uu ties both -> uu wins
    map_ops.add_unknown(m, "uu", "surprise")
    assert map_ops.dominant_quadrant(m) == "uu"
    # resolve uu; uk still >= ku -> uk
    map_ops.reclassify(m, "uu_1", status="resolved", technique="blindspot pass")
    assert map_ops.dominant_quadrant(m) == "uk"
    # high-severity uu beats larger counts elsewhere
    map_ops.add_unknown(m, "ku", "q2")
    map_ops.add_unknown(m, "ku", "q3")
    map_ops.add_unknown(m, "uu", "clock skew", severity="high")
    assert map_ops.dominant_quadrant(m) == "uu"


def test_missing_map_is_clear(tmp_path: Path):
    assert map_ops.dominant_quadrant(tmp_path / "nope.dot") == "clear"


def test_reclassify_moves_quadrant(seeded: Path):
    map_ops.prune_placeholders(seeded)
    nid = map_ops.add_unknown(seeded, "uu", "found it")
    map_ops.reclassify(seeded, nid, quadrant="ku", technique="blindspot pass")
    nodes = {n.node_id: n for n in map_ops.parse_map(seeded)}
    assert nodes[nid].quadrant == "ku"
    assert "reclassified via blindspot pass" in seeded.read_text()


def test_reclassify_unknown_node_raises(seeded: Path):
    with pytest.raises(KeyError):
        map_ops.reclassify(seeded, "nope_1", status="resolved")


def test_reclassify_without_final_metadata_does_not_mutate(tmp_path: Path):
    m = tmp_path / "legacy.dot"
    m.write_text('digraph G {\n  ku_1 [label="literal quadrant=ku, status=open"]\n}\n')
    before = m.read_bytes()
    assert map_ops.parse_map(m) == []
    assert map_ops.dominant_quadrant(m) == "clear"
    with pytest.raises(KeyError, match="not found"):
        map_ops.reclassify(m, "ku_1", status="resolved")
    assert m.read_bytes() == before


def test_prune_placeholders(seeded: Path):
    removed = map_ops.prune_placeholders(seeded)
    assert removed >= 4  # 4 placeholder nodes + 2 example edges
    # No placeholder NODES remain (template comments may still say "placeholder")
    assert map_ops.parse_map(seeded) == []
    assert "_placeholder [" not in seeded.read_text()
    assert "->" not in seeded.read_text()  # example edges gone too


def test_render_briefing_smoke(seeded: Path):
    map_ops.prune_placeholders(seeded)
    map_ops.add_unknown(seeded, "kk", "user wants a rate limiter", status="given")
    map_ops.add_unknown(seeded, "ku", "token refresh strategy", severity="high")
    map_ops.add_unknown(seeded, "uu", "legacy SAML users exist")
    out = map_ops.render_ascii(seeded)
    # Plain-language sections, no quadrant jargon
    assert "Open questions you know about (1)" in out
    assert "Blindspots surfaced (1)" in out
    assert "KNOWN UNKNOWNS" not in out and "quadrant" not in out
    # High severity marked, continuous numbering, start-here on dominant section
    assert "!! 1. token refresh strategy" in out
    assert "<- start here" in out
    # Header progress + NEXT action derived from triage (uu-high -> blindspot)
    assert "2 open / 3 total" in out
    assert "NEXT -> " in out and "blindspot pass" in out
    assert max(len(line) for line in out.splitlines()) <= 78


def test_render_briefing_wraps_never_truncates(seeded: Path):
    map_ops.prune_placeholders(seeded)
    long_desc = (
        "If the gateway runs multiple replicas, in-memory counters drift and "
        "your limits silently multiply unless state is shared, for example "
        "via Redis or another shared store"
    )
    map_ops.add_unknown(seeded, "ku", long_desc)
    out = map_ops.render_ascii(seeded)
    assert max(len(line) for line in out.splitlines()) <= 78
    # Rejoin wrapped lines: the full sentence survives, nothing elided
    flat = " ".join(part.strip() for part in out.splitlines())
    assert "silently multiply" in flat and "shared store" in flat
    assert "\u2026" not in out and "..." not in out.replace("... and", "")


def test_render_ascii_missing_map(tmp_path: Path):
    assert "no unknowns map" in map_ops.render_ascii(tmp_path / "nope.dot")
