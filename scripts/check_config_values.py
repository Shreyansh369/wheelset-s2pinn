"""Proof of every link in config/hash_aliases.yaml, and of a new link before it is added.

Results record the config hash in force when they were written. The aliases chain those hashes to the current
values-v2 hash (src/utils/results.py), so a result stays valid for the current configuration exactly when every
link in its chain is proven:

- a "byte" link (results written before values-v2): the byte hash of params.yaml + track.yaml at some commit maps to
  the values-v2 hash of the same values. Proof: the parsed values (source fields and comments removed) at the commit
  with that byte hash equal those at the latest commit with the target values-v2 hash. ANY numeric or structural
  difference fails.
- a "range-only" link: values-v2 hash F maps to T, and the only differences between the latest commit with F and
  the latest commit with T (or the working tree) are at the range fields named in the link ("allowed"), none of
  which is read by any computation.

    python3 scripts/check_config_values.py                 # verify every link; report the current hash
    python3 scripts/check_config_values.py --write         # first run: write the byte links
    python3 scripts/check_config_values.py --range-only --allow config/params.yaml:/axle/length/range ... [--write]
        # compare the working tree with the end of the chain; pass iff the only differences are the allowed
        # range fields; with --write, add the range-only link
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.utils.results import config_hash_bytes, config_hash_from_texts, config_values  # noqa: E402

FILES = ("params.yaml", "track.yaml")
LEGACY = {"e0a22f267362": "config", "10d9b91451c2": "config/snapshots/headline_freight_v1"}
ALIASES = ROOT / "config/hash_aliases.yaml"


def git(*a: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True, check=True).stdout


def show(rev: str, path: str) -> bytes | None:
    r = subprocess.run(["git", "-C", str(ROOT), "show", f"{rev}:{path}"], capture_output=True)
    return r.stdout if r.returncode == 0 else None


def files_at(d: str, rev: str | None) -> dict[str, bytes | None]:
    if rev is None:
        return {f: ((ROOT / d / f).read_bytes() if (ROOT / d / f).exists() else None) for f in FILES}
    return {f: show(rev, f"{d}/{f}") for f in FILES}


def v2(files: dict[str, bytes | None]) -> str:
    return config_hash_from_texts({f: (b.decode() if b is not None else None) for f, b in files.items()})


def commits(d: str) -> list[str]:
    return git("log", "--format=%H", "--", *(f"{d}/{f}" for f in FILES)).split()


def commit_with_byte_hash(d: str, want: str) -> str | None:
    return next((c for c in commits(d) if config_hash_bytes(files_at(d, c)) == want), None)


def latest_with_v2(d: str, want: str) -> str | None:
    return next((c for c in commits(d) if v2(files_at(d, c)) == want), None)


def diff(a, b, path=""):
    """(path, message) for every difference between two parsed configs."""
    if type(a) is not type(b):
        return [(path or "/", f"type {type(a).__name__} -> {type(b).__name__} ({a!r} -> {b!r})")]
    if isinstance(a, dict):
        out = [(f"{path}/{k}", "removed") for k in sorted(set(a) - set(b))]
        out += [(f"{path}/{k}", f"added ({b[k]!r})") for k in sorted(set(b) - set(a))]
        for k in sorted(set(a) & set(b)):
            out += diff(a[k], b[k], f"{path}/{k}")
        return out
    if isinstance(a, list):
        if len(a) != len(b):
            return [(path, f"list {a!r} -> {b!r}")]
        return [x for i, (u, w) in enumerate(zip(a, b)) for x in diff(u, w, f"{path}[{i}]")]
    return [] if a == b else [(path, f"{a!r} -> {b!r}")]


def config_diff(d: str, old: dict, new: dict) -> list[tuple[str, str]]:
    out = []
    for f in FILES:
        if (old[f] is None) != (new[f] is None):
            out.append((f"{d}/{f}:/", "file added" if old[f] is None else "file removed"))
        elif old[f] is not None:
            out += [(f"{d}/{f}:{p}", m) for p, m in diff(config_values(old[f].decode()), config_values(new[f].decode()))]
    return out


def allowed(path: str, allow: list[str]) -> bool:
    return any(path == a or path.startswith(a + "[") or path.startswith(a + "/") for a in allow)


def load_aliases() -> dict:
    return yaml.safe_load(ALIASES.read_text()) if ALIASES.exists() else {"aliases": {}, "proof": {}}


def chain_end(h: str, al: dict) -> str:
    seen = {h}
    while h in al:
        h = al[h]
        if h in seen:
            raise SystemExit(f"alias cycle at {h}")
        seen.add(h)
    return h


def verify_links(doc: dict) -> bool:
    ok = True
    for src, p in (doc.get("proof") or {}).items():
        d, tgt, kind = p["config_dir"], doc["aliases"][src], p.get("type", "byte")
        if kind == "byte":
            c_old = commit_with_byte_hash(d, src)
        else:
            c_old = latest_with_v2(d, src)
        c_new = latest_with_v2(d, tgt)
        new = files_at(d, c_new) if c_new else files_at(d, None)
        if c_old is None or (c_new is None and v2(new) != tgt):
            print(f"FAIL link {src} -> {tgt} ({d}): commit not found (old {c_old}, new {c_new})")
            ok = False
            continue
        dd = config_diff(d, files_at(d, c_old), new)
        allow = p.get("allowed") or []
        bad = [x for x in dd if not allowed(x[0], allow)]
        where = f"{c_old[:7]} -> {c_new[:7] if c_new else 'working tree'}"
        if bad:
            ok = False
            print(f"FAIL link {src} -> {tgt} ({kind}, {d}, {where}): {len(bad)} difference(s) outside the allowed fields")
            for x in bad:
                print("    ", *x)
        else:
            print(f"PASS link {src} -> {tgt} ({kind}, {d}, {where}): "
                  + ("no numeric or structural difference" if not dd else f"only the allowed range fields differ ({len(dd)})"))
            for x in dd:
                print("     ", *x)
    return ok


def write_aliases(doc: dict) -> None:
    lines = ["# Config hashes recorded by results -> the values-v2 hash they are valid for (chains are followed).",
             "# Written by scripts/check_config_values.py --write after it proved each link; make_provenance_check.py",
             "# accepts a recorded hash whose chain ends at the current values-v2 hash. Do not edit by hand.",
             "aliases:"]
    lines += [f"  \"{k}\": \"{v}\"" for k, v in doc["aliases"].items()]
    lines += ["proof:"]
    for k, p in doc["proof"].items():
        lines += [f"  \"{k}\":"]
        for kk, vv in p.items():
            lines += [f"    {kk}: [" + ", ".join(f"\"{x}\"" for x in vv) + "]" if isinstance(vv, list) else f"    {kk}: \"{vv}\""]
    ALIASES.write_text("\n".join(lines) + "\n")
    print("wrote config/hash_aliases.yaml")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--range-only", action="store_true", help="propose a range-only link from the chain end to the working tree")
    ap.add_argument("--allow", nargs="*", default=[], help="range fields allowed to differ, e.g. config/params.yaml:/axle/length/range")
    ap.add_argument("--dir", default="config")
    a = ap.parse_args()
    doc = load_aliases()
    doc.setdefault("aliases", {})
    doc.setdefault("proof", {})
    head = git("rev-parse", "HEAD").strip()
    date = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if not doc["aliases"]:                     # first run: the byte links
        ok = True
        for legacy, d in LEGACY.items():
            c = commit_with_byte_hash(d, legacy)
            if c is None:
                print(f"FAIL {legacy} ({d}): no commit has this byte hash")
                ok = False
                continue
            new = files_at(d, None)
            dd = config_diff(d, files_at(d, c), new)
            if dd:
                ok = False
                print(f"FAIL {legacy} ({d}): {len(dd)} difference(s)")
            else:
                doc["aliases"][legacy] = v2(new)
                doc["proof"][legacy] = {"type": "byte", "config_dir": d, "byte_hash_commit": c, "values_v2": v2(new),
                                        "checked_against": f"working tree at {head}", "date": date}
        if ok and a.write:
            write_aliases(doc)
        return 0 if ok else 1
    ok = verify_links(doc)
    if a.range_only:
        d = a.dir
        end = chain_end(next(k for k, p in doc["proof"].items() if p["config_dir"] == d and p.get("type", "byte") == "byte"),
                        doc["aliases"])
        c_old = latest_with_v2(d, end)
        new = files_at(d, None)
        h_new = v2(new)
        dd = config_diff(d, files_at(d, c_old), new)
        bad = [x for x in dd if not allowed(x[0], a.allow)]
        print(f"range-only {d}: chain end {end} at {c_old[:7]} -> working tree {h_new}: {len(dd)} difference(s)")
        for x in dd:
            print("     ", "ALLOWED" if allowed(x[0], a.allow) else "NOT ALLOWED", *x)
        if bad or not dd or not a.allow:
            print("FAIL range-only: " + ("differences outside the allowed fields" if bad else "nothing to link"))
            return 1
        print("PASS range-only: the only differences are the allowed range fields")
        if ok and a.write:
            doc["aliases"][end] = h_new
            doc["proof"][end] = {"type": "range-only", "config_dir": d, "from_commit": c_old, "values_v2": h_new,
                                 "allowed": list(a.allow), "proving_commit": head, "checked_against": f"working tree at {head}",
                                 "note": "the allowed range fields are read by no computation (Table 1 display only)", "date": date}
            write_aliases(doc)
    for d in sorted({p["config_dir"] for p in doc["proof"].values()}):
        h = v2(files_at(d, None))
        ends = {chain_end(k, doc["aliases"]) for k, p in doc["proof"].items() if p["config_dir"] == d}
        st = "chain ends here" if h in ends else "NOT the end of any chain"
        print(f"current {d}: values-v2 {h} ({st})")
        ok = ok and (h in ends or a.range_only)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
