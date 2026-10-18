"""Proof that the configuration's values have not moved since the byte hashes recorded in the results.

Results written before 19 Oct 2026 record the byte hash of params.yaml + track.yaml (e0a22f267362 for config/,
10d9b91451c2 for the pinned snapshot config/snapshots/headline_freight_v1). For each, this script finds the
commit whose files have that byte hash, parses those files and the current ones (working tree, or --rev), and
fails on ANY numeric or structural difference of the parsed YAML once source fields and comments are removed
(the content of the values-v2 hash, src/utils/results.py). Units and other non-source strings count.

    python3 scripts/check_config_values.py            # check; exit 1 on any difference
    python3 scripts/check_config_values.py --write    # check, then write config/hash_aliases.yaml
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.utils.results import config_hash_bytes, config_hash_from_texts, config_values  # noqa: E402

FILES = ("params.yaml", "track.yaml")
LEGACY = {"e0a22f267362": "config", "10d9b91451c2": "config/snapshots/headline_freight_v1"}


def git(*a: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True, check=True).stdout


def show(rev: str, path: str) -> bytes | None:
    r = subprocess.run(["git", "-C", str(ROOT), "show", f"{rev}:{path}"], capture_output=True)
    return r.stdout if r.returncode == 0 else None


def commit_with_byte_hash(d: str, want: str) -> str | None:
    for c in git("log", "--format=%H", "--", *(f"{d}/{f}" for f in FILES)).split():
        if config_hash_bytes({f: show(c, f"{d}/{f}") for f in FILES}) == want:
            return c
    return None


def diff(a, b, path="") -> list[str]:
    if type(a) is not type(b):
        return [f"{path or '/'}: type {type(a).__name__} -> {type(b).__name__} ({a!r} -> {b!r})"]
    if isinstance(a, dict):
        out = [f"{path}/{k}: removed" for k in sorted(set(a) - set(b))]
        out += [f"{path}/{k}: added ({b[k]!r})" for k in sorted(set(b) - set(a))]
        for k in sorted(set(a) & set(b)):
            out += diff(a[k], b[k], f"{path}/{k}")
        return out
    if isinstance(a, list):
        if len(a) != len(b):
            return [f"{path}: list length {len(a)} -> {len(b)}"]
        return [x for i, (u, v) in enumerate(zip(a, b)) for x in diff(u, v, f"{path}[{i}]")]
    return [] if a == b else [f"{path}: {a!r} -> {b!r}"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rev", default=None, help="compare against this revision instead of the working tree")
    ap.add_argument("--write", action="store_true", help="write config/hash_aliases.yaml when every check passes")
    a = ap.parse_args()
    head = git("rev-parse", "HEAD").strip()
    ok, aliases, proof = True, {}, {}
    for legacy, d in LEGACY.items():
        c = commit_with_byte_hash(d, legacy)
        if c is None:
            print(f"FAIL {legacy} ({d}): no commit has this byte hash")
            ok = False
            continue
        old = {f: show(c, f"{d}/{f}") for f in FILES}
        if a.rev:
            new = {f: show(a.rev, f"{d}/{f}") for f in FILES}
        else:
            new = {f: ((ROOT / d / f).read_bytes() if (ROOT / d / f).exists() else None) for f in FILES}
        dd = []
        for f in FILES:
            if (old[f] is None) != (new[f] is None):
                dd.append(f"{d}/{f}: file {'added' if old[f] is None else 'removed'}")
            elif old[f] is not None:
                dd += [f"{d}/{f}{x}" for x in diff(config_values(old[f].decode()), config_values(new[f].decode()))]
        h_old = config_hash_from_texts({f: (old[f].decode() if old[f] is not None else None) for f in FILES})
        h_new = config_hash_from_texts({f: (new[f].decode() if new[f] is not None else None) for f in FILES})
        byte_new = config_hash_bytes(new)
        print(f"{d}: byte hash {legacy} at {c[:7]}; now byte {byte_new}; values-v2 {h_old} at {c[:7]}, {h_new} now")
        if dd or h_old != h_new:
            ok = False
            print(f"FAIL {d}: {len(dd)} difference(s) in the values")
            for x in dd:
                print("   ", x)
        else:
            print(f"PASS {d}: no numeric or structural difference (sources and comments ignored)")
            aliases[legacy] = h_new
            proof[legacy] = {"config_dir": d, "byte_hash_commit": c, "values_v2": h_new,
                             "checked_against": a.rev or f"working tree at {head}"}
    if ok and a.write:
        date = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        lines = ["# Byte config hashes (recorded before values-v2) -> values-v2 hash of the same values.",
                 "# Written by scripts/check_config_values.py --write after it found no numeric or structural",
                 "# difference; make_provenance_check.py accepts an aliased recorded hash. Do not edit by hand.",
                 "aliases:"]
        lines += [f"  \"{k}\": \"{v}\"" for k, v in aliases.items()]
        lines += ["proof:"]
        for k, p in proof.items():
            lines += [f"  \"{k}\":"] + [f"    {kk}: \"{vv}\"" for kk, vv in p.items()] + [f"    date: \"{date}\""]
        (ROOT / "config/hash_aliases.yaml").write_text("\n".join(lines) + "\n")
        print("wrote config/hash_aliases.yaml")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
