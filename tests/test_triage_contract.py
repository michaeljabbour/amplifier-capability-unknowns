"""Contract test: the Python triage and the zero-dep shell mirror NEVER drift.

scripts/dominant_quadrant.sh is what the pipeline's parallelogram guard shells
in bare environments; unknowns_map.dominant_quadrant is the canonical Python
home. This test builds maps covering every precedence branch and asserts both
implementations emit the same routing token.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

from unknowns_map import map_ops
from unknowns_map._assets import triage_script

pytestmark = pytest.mark.skipif(
    shutil.which("bash") is None, reason="bash not available"
)


def _shell_triage(map_path: Path) -> str:
    proc = subprocess.run(
        ["bash", str(triage_script()), str(map_path)],
        capture_output=True, text=True, check=True,
    )
    return proc.stdout.strip().splitlines()[-1]


SCENARIOS = [
    ("empty", []),
    ("ku_only", [("ku", "med"), ("ku", None)]),
    ("uk_beats_ku_tie", [("ku", None), ("uk", None)]),
    ("ku_majority", [("ku", None), ("ku", None), ("uk", None)]),
    ("uu_tie_wins", [("ku", None), ("uk", None), ("uu", "med")]),
    ("uu_high_trumps", [("ku", None), ("ku", None), ("ku", None), ("uu", "high")]),
    ("uu_outnumbered_low", [("ku", None), ("ku", None), ("uu", "med")]),
]


@pytest.mark.parametrize("name,adds", SCENARIOS, ids=[s[0] for s in SCENARIOS])
def test_python_matches_shell(tmp_path: Path, name: str, adds):
    m = tmp_path / "map.dot"
    map_ops.seed_map(m, task=name)
    map_ops.prune_placeholders(m)
    for quadrant, severity in adds:
        map_ops.add_unknown(m, quadrant, f"item in {quadrant}", severity=severity)
    assert map_ops.dominant_quadrant(m) == _shell_triage(m)


def test_missing_map_parity(tmp_path: Path):
    missing = tmp_path / "nope.dot"
    assert map_ops.dominant_quadrant(missing) == _shell_triage(missing) == "clear"


@pytest.mark.parametrize("desc", [
    "Can export preserve\nall Unicode?",
    "first\rsecond",
    "first\r\nsecond",
    'Keep "quotes", C:\\new\\reports\\, literal \\n, and café 中文 🧭',
])
def test_escaped_description_triage_parity(tmp_path: Path, desc: str):
    m = tmp_path / "escaped.dot"
    map_ops.seed_map(m)
    map_ops.prune_placeholders(m)
    nid = map_ops.add_unknown(m, "ku", desc)
    assert map_ops.dominant_quadrant(m) == _shell_triage(m) == "ku"
    map_ops.reclassify(m, nid, quadrant="uu", severity="high")
    assert map_ops.dominant_quadrant(m) == _shell_triage(m) == "uu"
    map_ops.reclassify(m, nid, status="resolved")
    assert map_ops.dominant_quadrant(m) == _shell_triage(m) == "clear"
