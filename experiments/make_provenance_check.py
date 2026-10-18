"""Provenance check: every table, figure and macro of the paper against the frozen configuration.

Sources: results/tables/manifest.json (make_tables.py), figures/manifest.json (make_figures.py) and
paper/generated/macro_sources.json (make_paper_numbers.py) give the result files behind each item;
config/provenance.yaml declares the configuration (frozen / pinned / earlier) and estimator of each file.
Result files that record provenance.config_hash and estimator_version are checked against the declaration
(frozen = hash of config/params.yaml + config/track.yaml; pinned = config/snapshots/headline_freight_v1).

Fails (exit 1) when
  - a source file is not declared;
  - a recorded config hash or estimator version contradicts the declaration;
  - a table or figure with a non-frozen source lacks the label ("earlier configuration" or "pinned
    headline configuration") in its caption;
  - a macro with a non-frozen source is used in a paragraph that lacks the label, or at all in the abstract
    or conclusions.
Writes docs/provenance.md (all items, and the list of results that still carry an earlier-configuration
label). Run after make_tables.py, make_figures.py and make_paper_numbers.py.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.utils.results import config_hash  # noqa: E402

REG = yaml.safe_load((ROOT / "config/provenance.yaml").read_text())
FROZEN, PINNED = config_hash(ROOT / "config"), config_hash(ROOT / "config/snapshots/headline_freight_v1")
# byte hashes recorded before values-v2 -> values-v2 hash of the same values (proof: scripts/check_config_values.py)
_AL = ROOT / "config/hash_aliases.yaml"
ALIASES = (yaml.safe_load(_AL.read_text()) or {}).get("aliases", {}) if _AL.exists() else {}


def hash_match(rec, want):
    """'v2' when the recorded hash is the values-v2 hash, 'alias' when it is a byte hash aliased to it, else None."""
    if rec == want:
        return "v2"
    if ALIASES.get(rec) == want:
        return "alias"
    return None
TEX = ["abstract", "sec1_intro", "sec2_model", "sec3_method", "sec4_results", "sec5_discussion", "sec6_conclusions", "backmatter"]
STRICT = ("abstract", "sec6_conclusions")


def strip(t):
    return re.sub(r"(?<!\\)%.*", "", t)


def declared(src, macro=None):
    e = REG["files"].get(src)
    if e is None:
        return None
    if macro:
        for pre, c in (e.get("macro_overrides") or {}).items():
            if macro.startswith(pre):
                return dict(e, config=c)
    return e


def has_label(text, cfg):
    return REG["labels"][cfg] in re.sub(r"\s+", " ", text)


def main():
    fails, rows, earlier = [], [], set()
    # ---- result files: declaration vs recorded provenance
    T = json.loads((ROOT / "results/tables/manifest.json").read_text())
    F = json.loads((ROOT / "figures/manifest.json").read_text())
    M = json.loads((ROOT / "paper/generated/macro_sources.json").read_text())
    files = sorted({s for v in T.values() for s in v["sources"]} | {s for v in F.values() for s in v} | set(M.values()))
    fstat = {}
    for src in files:
        e = declared(src)
        if e is None:
            fails.append(f"undeclared source `{src}`")
            fstat[src] = ("UNDECLARED", "-", "-")
            continue
        rec_h, rec_e, note = "-", "-", "declared"
        fp = ROOT / src
        if fp.suffix == ".json" and fp.exists():
            p = json.loads(fp.read_text()).get("provenance", {})
            rec_h, rec_e = p.get("config_hash") or "-", p.get("estimator_version") or "-"
            want = {"frozen": FROZEN, "pinned": PINNED}.get(e["config"])
            if e["config"] == "sensitivity":       # an override config directory with its own hash
                want = config_hash(ROOT / e["config_dir"])
            if rec_h != "-":
                how = hash_match(rec_h, want) if want else None
                if want and how is None:
                    fails.append(f"`{src}` declared {e['config']} but recorded config hash {rec_h}")
                    note = "HASH MISMATCH"
                elif not want and hash_match(rec_h, FROZEN):
                    note = "declared earlier, hash is frozen (declaration conservative)"
                elif how == "alias":
                    note = f"hash verified (byte hash, alias of {want})"
                else:
                    note = "hash verified (values-v2)"
            if rec_e != "-" and e["config"] in ("frozen", "pinned", "sensitivity") and rec_e != REG["frozen_estimator"] and "estimator" not in e:
                fails.append(f"`{src}` estimator version {rec_e!r} differs from the frozen estimator")
        fstat[src] = (e["config"], rec_h, note)
        if e["config"] == "earlier":
            earlier.add(src)
    # ---- tables
    paper = {n: strip((ROOT / f"paper/{n}.tex").read_text()) for n in TEX}
    allt = "\n".join(paper.values())
    used_tables = re.findall(r"\\inputtable\{(\w+)\}", allt)
    for name in used_tables:
        v = T.get(name)
        if v is None:
            fails.append(f"table {name} not in manifest")
            continue
        cfgs = {(declared(s) or {"config": "UNDECLARED"})["config"] for s in v["sources"]}
        need = [c for c in ("earlier", "pinned", "sensitivity") if c in cfgs]
        ok = all(has_label(v["caption"], c) for c in need)
        if not ok:
            fails.append(f"table {name}: sources {sorted(cfgs)} but caption lacks label(s) {need}")
        rows.append(("table", name, ", ".join(v["sources"]), "/".join(sorted(cfgs)), "ok" if ok else "MISSING LABEL"))
    # ---- figures (caption from the paper)
    for env in re.findall(r"\\begin\{figure\}.*?\\end\{figure\}", allt, flags=re.S):
        g = re.search(r"\\includegraphics(?:\[[^]]*\])?\{([\w.]+)\}", env)
        if not g:
            continue
        name = g.group(1).replace(".pdf", "")
        cap = env[env.find("\\caption"):]
        srcs = F.get(name, [])
        cfgs = {(declared(s) or {"config": "UNDECLARED"})["config"] for s in srcs}
        need = [c for c in ("earlier", "pinned", "sensitivity") if c in cfgs]
        ok = bool(srcs) and all(has_label(cap, c) for c in need)
        if not srcs:
            fails.append(f"figure {name} not in manifest")
        elif not ok:
            fails.append(f"figure {name}: sources {sorted(cfgs)} but caption lacks label(s) {need}")
        rows.append(("figure", name, ", ".join(srcs), "/".join(sorted(cfgs)), "ok" if ok else "MISSING LABEL"))
    # ---- macros, paragraph by paragraph
    mrows = {}
    for n, t in paper.items():
        for par in re.split(r"\n\s*\n", t):
            for mac in sorted(set(re.findall(r"\\([A-Za-z]+)", par))):
                if mac not in M:
                    continue
                e = declared(M[mac], mac) or {"config": "UNDECLARED"}
                c = e["config"]
                if c == "frozen":
                    st = "ok"
                elif c == "UNDECLARED":
                    st = "UNDECLARED"
                elif n in STRICT:
                    st = f"NOT FROZEN in {n}"
                    fails.append(f"macro \\{mac} ({M[mac]}, {c}) used in {n}")
                elif has_label(par, c):
                    st = "labelled"
                else:
                    st = "MISSING LABEL"
                    fails.append(f"macro \\{mac} ({M[mac]}, {c}) in {n}: paragraph lacks '{REG['labels'][c]}'")
                prev = mrows.get(mac)
                if prev is None or prev[3] in ("ok", "labelled"):
                    mrows[mac] = (M[mac], c, n, st)
    # ---- report
    out = ["# Provenance check", "",
           f"Frozen configuration hash `{FROZEN}` (config/params.yaml + config/track.yaml); pinned headline "
           f"configuration `{PINNED}` (values-v2 hashes; byte hashes recorded earlier are accepted through "
           f"`config/hash_aliases.yaml`: {', '.join(f'{k} -> {v}' for k, v in ALIASES.items()) or 'none'}); "
           f"frozen estimator: {REG['frozen_estimator']}. Generated by "
           "`python3 experiments/make_provenance_check.py`; declarations in `config/provenance.yaml`.", "",
           f"**Result: {'PASS' if not fails else 'FAIL (' + str(len(fails)) + ')'}**", ""]
    if fails:
        out += ["## Failures", ""] + [f"- {x}" for x in fails] + [""]
    out += ["## Results that still carry an earlier-configuration label", ""]
    out += [f"- `{s}`: {REG['files'][s].get('setup', '')}" for s in sorted(earlier)] or ["- none"]
    out += ["", "## Result files", "", "| File | Declared | Recorded config hash | Status |", "|---|---|---|---|"]
    out += [f"| `{s}` | {fstat[s][0]} | {fstat[s][1]} | {fstat[s][2]} |" for s in files]
    out += ["", "## Tables and figures", "", "| Item | Name | Sources | Config | Caption label |", "|---|---|---|---|---|"]
    out += [f"| {a} | {b} | {c} | {d} | {e} |" for a, b, c, d, e in rows]
    out += ["", "## Macros used in the paper", "", "| Macro | Source | Config | First use | Status |", "|---|---|---|---|---|"]
    out += [f"| `\\{k}` | {v[0]} | {v[1]} | {v[2]} | {v[3]} |" for k, v in sorted(mrows.items())]
    (ROOT / "docs/provenance.md").write_text("\n".join(out) + "\n")
    print(f"provenance: {'PASS' if not fails else 'FAIL'} ({len(fails)} failures); earlier-labelled results: {len(earlier)}")
    for x in fails:
        print("  -", x)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
