"""Merge the preregistration-v2 result rows of the four sessions (docs/preregistration_v2_addendum.md).

Session s0 writes on this branch; s1-s3 push claude/rows-s1 ... -s3. For every study the per-session files
(suffix _v2_sN) are read, from this working tree for s0 and with `git show` from origin/claude/rows-sN for the
others, rows are deduplicated by their seed key (first occurrence kept, in session order), and the merged file
(suffix _v2) is written. Each merged row carries "_src": {"session", "branch", "commit", "file"}; the commit is
the one that added the row (`git blame` on the source branch). The summary of what came from where is written to
results/p5/merge_provenance.json. Rows committed after --cutoff (preregistration_v2_addendum §5) are left out.

    git fetch origin claude/rows-s1 claude/rows-s2 claude/rows-s3
    python3 scripts/merge_rows_v2.py --cutoff 2026-11-03T06:00:00Z
"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = "claude/inspiring-cori-690nu3"
SESS = {0: WORK, 1: "claude/rows-s1", 2: "claude/rows-s2", 3: "claude/rows-s3"}

# merged file (relative to results/) -> (per-session file pattern with {s}, key function)
STUDIES = {
    "p3/headline_v2_runs/kb120_attr_v2.jsonl": ("p3/headline_v2_runs/kb120_attr_v2_s{s}.jsonl", lambda r: tuple(r["seed_key"])),
    "p3/headline_v2_runs/kb120_attr_kb0_2p5_v2.jsonl": ("p3/headline_v2_runs/kb120_attr_kb0_2p5_v2_s{s}.jsonl", lambda r: tuple(r["seed_key"])),
    "p3/headline_v2_runs/kb120_attr_kb0_5p0_v2.jsonl": ("p3/headline_v2_runs/kb120_attr_kb0_5p0_v2_s{s}.jsonl", lambda r: tuple(r["seed_key"])),
    "p4/banded_runs/bounds_v2.jsonl": ("p4/banded_runs/bounds_v2_s{s}.jsonl", lambda r: (r["band"], r["N"], r["snr_db"])),
    "p5/runs/simerr_v2.jsonl": ("p5/runs/simerr_v2_s{s}.jsonl", lambda r: r["rep"]),
    "p5/runs/zero_v2.jsonl": ("p5/runs/zero_v2_s{s}.jsonl", lambda r: r["rep"]),
    "p5/runs/simerr_v2_fits.jsonl": ("p5/runs/simerr_v2_s{s}_fits.jsonl", lambda r: (r["rep"], r["period"], r["start"])),
    "p5/runs/zero_v2_fits.jsonl": ("p5/runs/zero_v2_s{s}_fits.jsonl", lambda r: (r["rep"], r["period"], r["start"])),
    "p4/sweep_runs_v2.jsonl": ("p4/sweep_runs_v2_s{s}.jsonl", lambda r: (r["param"], r["point"], r["value"])),
    **{f"p4/inverse_crime_runs/{m}_v2.jsonl": (f"p4/inverse_crime_runs/{m}_v2_s{{s}}.jsonl", lambda r: tuple(r["key"]))
       for m in ("nl", "lin", "pairs", "pairsx")},
    **{f"p2/model_form_mw_runs_v2/{e}__{p}.jsonl": (f"p2/model_form_mw_runs_v2_s{{s}}/{e}__{p}.jsonl", lambda r: round(r["factor"], 6))
       for e in ("nominal", "coest") for p in ("kf", "eta_f", "kH0", "unsprung_scale", "axle_damp_scale")},
}


def git(*a, check=True):
    return subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True, check=check).stdout


def lines_with_commits(ref, path):
    """[(line, commit, commit time)] of results/<path> at ref; ref None = this working tree (s0)."""
    rel = f"results/{path}"
    if ref is None:
        fp = ROOT / rel
        if not fp.exists():
            return []
        out = git("blame", "--line-porcelain", "--", rel, check=False)
    else:
        out = git("blame", "--line-porcelain", ref, "--", rel, check=False)
    rows, commit, t = [], None, None
    for l in out.splitlines():
        if len(l) >= 40 and not l.startswith("\t") and " " in l and all(c in "0123456789abcdef" for c in l.split(" ")[0]) and len(l.split(" ")[0]) == 40:
            commit = l.split(" ")[0]
        elif l.startswith("committer-time "):
            t = int(l.split(" ")[1])
        elif l.startswith("\t"):
            rows.append((l[1:], commit, t))
    if ref is None and not rows and (ROOT / rel).exists():     # file not yet committed: no commit to record
        rows = [(l, None, None) for l in (ROOT / rel).read_text().splitlines()]
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cutoff", default=None, help="ISO time; rows committed later are left out")
    a = ap.parse_args()
    cut = datetime.fromisoformat(a.cutoff.replace("Z", "+00:00")).timestamp() if a.cutoff else None
    prov = {"cutoff": a.cutoff, "sessions": SESS, "files": {}}
    for merged, (pat, key) in STUDIES.items():
        seen, out, src = set(), [], {}
        for s, br in SESS.items():
            path = pat.format(s=s)
            for line, commit, t in lines_with_commits(None if s == 0 else f"origin/{br}", path):
                if not line.strip():
                    continue
                if cut and t and t > cut:
                    continue
                r = json.loads(line)
                k = key(r)
                if k in seen:
                    continue
                seen.add(k)
                r["_src"] = {"session": f"s{s}", "branch": br, "commit": commit, "file": f"results/{path}"}
                out.append(r)
                src[f"s{s}"] = src.get(f"s{s}", 0) + 1
        if out:
            fp = ROOT / "results" / merged
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text("".join(json.dumps(r) + "\n" for r in out))
            prov["files"][f"results/{merged}"] = {"rows": len(out), "rows_per_session": src}
    prov["written_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    (ROOT / "results" / "p5" / "merge_provenance.json").write_text(json.dumps(prov, indent=1) + "\n")
    print(json.dumps(prov["files"], indent=1))


if __name__ == "__main__":
    main()
