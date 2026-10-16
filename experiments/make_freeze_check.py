"""docs/freeze_check.md: every number in the abstract, highlights, conclusions and cover letter, checked
against the generated macros, with its source result file and the configuration it was computed with.

Macros are read from paper/generated/numbers.tex; numbers typed into the highlights and the cover letter
(which cannot use macros) are compared with the macro they quote. Run after make_paper_numbers.py.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CUR = "current (representative wagon, Table 1)"
HL = "current wagon, but k_H0 1.4 GN/m and c_p 10 kN s/m (pinned headline config)"
OLD = "EARLIER (metro layout, BS113A, +-30-bin kernel)"
SRC = [  # (macro prefix, source file, configuration)
    ("HL", "results/p3/headline_v2_kb120_attr_freight.json", HL),
    ("IgnoreCoupling", "results/p4/ignore_coupling.json", CUR),
    ("IC", "results/p4/inverse_crime.json", CUR),
    ("Budget", "results/p2/model_form_mw_sensitivity.json", CUR),
    ("MDCCal", "results/p3/calibrated.json <- results/p4/mdc_bounds.json (calibration from the headline)", CUR + "; calibration factor from " + HL),
    ("MDC", "results/p4/mdc_bounds.json via results/p3/calibrated.json", CUR),
    ("DriftMC", "results/p2/relative_coest_drift.json (drift Monte Carlo)", OLD),
    ("Drift", "results/p2/drift_freight.json", CUR),
    ("EffPctTen", "results/p3/bearing_clearance.json", CUR),
    ("Kap", "results/p3/validation_mc.json / calibrated.json", OLD),
]
TYPED = [  # (file, literal number as typed, macro it quotes)
    ("paper/submission/highlights.txt", "5.6%", "IgnoreCouplingForty"),
    ("paper/submission/cover_letter.tex", "5.6\\%", "IgnoreCouplingForty"),
]


def source(name):
    for pre, f, cfg in SRC:
        if name.startswith(pre):
            return f, cfg
    return "?", "?"


def main():
    m = dict(re.findall(r"\\newcommand\{\\(\w+)\}\{([^}]*)\}", (ROOT / "paper/generated/numbers.tex").read_text()))
    out = ["# Freeze cross-check", "",
           "Every number in the abstract, highlights, conclusions and cover letter, with the generated value, the result "
           "file it comes from and the configuration it was computed with. Regenerate with "
           "`python3 experiments/make_freeze_check.py` after `make_paper_numbers.py`.", ""]
    older = []
    for f in ("paper/abstract.tex", "paper/sec6_conclusions.tex"):
        t = re.sub(r"(?<!\\)%.*", "", (ROOT / f).read_text())
        names = []
        for n in re.findall(r"\\(\w+)", t):
            if n in m and n not in names:
                names.append(n)
        out += [f"## {f}", "", "| Macro | Value | Source | Configuration |", "|---|---|---|---|"]
        for n in names:
            s, cfg = source(n)
            out.append(f"| `\\{n}` | {m[n]} | {s} | {cfg} |")
            if cfg.startswith("EARLIER"):
                older.append(f"{f}: \\{n} = {m[n]}")
        out.append("")
    out += ["## Numbers typed by hand (highlights, cover letter)", "", "| File | Typed | Macro | Macro value | Match |", "|---|---|---|---|---|"]
    for f, lit, mac in TYPED:
        present = lit in (ROOT / f).read_text()
        val = m.get(mac, "?")
        match = present and lit.replace("\\", "").rstrip("%") == val.lstrip("-")
        out.append(f"| {f} | {lit if present else '(not found)'} | `\\{mac}` | {val} | {'yes' if match else 'NO'} |")
    out += ["", "## Numbers from an older configuration", ""]
    out += [f"- {x}" for x in older] or ["- none in the abstract or conclusions"]
    out += ["", "Other numbers in these texts are design values (50/200 passes, 60–110 km/h, 20/40 dB, 22.5 t, 10 µm, 20 %), "
            "not results."]
    (ROOT / "docs/freeze_check.md").write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
