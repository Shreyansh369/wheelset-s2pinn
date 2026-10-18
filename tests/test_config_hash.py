"""values-v2 config hash: source fields and comments do not count, every value does."""

import importlib.util
from pathlib import Path

from src.utils.results import config_hash_from_texts, config_values

ROOT = Path(__file__).resolve().parents[1]
P = (ROOT / "config/params.yaml").read_text()
T = (ROOT / "config/track.yaml").read_text()
H = config_hash_from_texts({"params.yaml": P, "track.yaml": T})
spec = importlib.util.spec_from_file_location("ccv", ROOT / "scripts/check_config_values.py")
ccv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ccv)


def test_source_and_comment_edits_keep_hash():
    p2 = "# a new comment\n" + P.replace('source: "brief; configurable (Child A hook)"', 'source: "changed citation"')
    assert p2 != P
    assert config_hash_from_texts({"params.yaml": p2, "track.yaml": T}) == H


def test_value_and_unit_edits_change_hash_and_are_reported():
    for old, new in (("kB0:       {value: 1.0e9,", "kB0:       {value: 1.1e9,"), ("unit: N/m, range: [0.5e9", "unit: kN/m, range: [0.5e9")):
        assert old in P
        p2 = P.replace(old, new, 1)
        assert config_hash_from_texts({"params.yaml": p2, "track.yaml": T}) != H
        assert ccv.diff(config_values(P), config_values(p2))
