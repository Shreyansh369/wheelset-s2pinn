"""Assemble the MSSP submission folder (paper/submission/build) from the paper sources.

Contents: main.tex and every source it inputs (sections, abstract, authors, back matter, refs.bib,
generated/numbers.tex, tables/*.tex), main.bbl, figures renamed Figure_1.pdf ... in order of first
citation (vector PDFs from figures/, \\includegraphics rewritten accordingly), highlights (.docx and .txt),
cover letter (.tex and .pdf), and a compiled main.pdf for checking. Checks: figure order (first citation
vs numbering), highlights length (<= 85 characters, 3-5 bullets), abstract length (<= 250 words), no
vertical rules in tables, no unresolved references. Writes paper/submission/build/CHECKS.txt.
Run after `make -C paper` (needs main.aux and main.bbl).
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
SUB = PAPER / "submission"
OUT = SUB / "build"
SECTIONS = ["sec1_intro", "sec2_model", "sec3_method", "sec4_results", "sec5_discussion", "sec6_conclusions"]
SOURCES = ["main", "authors", "abstract", *SECTIONS, "backmatter"]


def figure_order():
    """(label, file) of each figure in order of first citation in the text."""
    text = "".join((PAPER / f"{s}.tex").read_text() for s in SECTIONS)
    figs = re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}.*?\\label\{(fig:[^}]+)\}", text, re.S)
    lab2file = {lab: f for f, lab in figs}
    cites = []
    for m in re.finditer(r"\\ref\{(fig:[^}]+)\}", text):
        if m.group(1) not in cites:
            cites.append(m.group(1))
    order = [lab for lab in cites if lab in lab2file] + [lab for lab in lab2file if lab not in cites]
    numbered = [lab for _, lab in figs]        # LaTeX numbers floats in order of appearance
    return [(lab, lab2file[lab]) for lab in order], order == numbered, numbered


def abstract_words():
    m = dict(re.findall(r"\\newcommand\{\\(\w+)\}\{([^}]*)\}", (PAPER / "generated/numbers.tex").read_text()))
    t = (PAPER / "abstract.tex").read_text()
    t = re.sub(r"(?<!\\)%.*", "", t)
    t = re.sub(r"\\(begin|end)\{abstract\}", "", t)
    t = re.sub(r"\\(\w+)(\{\})?", lambda x: m.get(x.group(1), ""), t)
    return len(t.split())


def highlights():
    lines = [l[2:].strip() for l in (SUB / "highlights.txt").read_text().splitlines() if l.startswith("- ")]
    from docx import Document
    doc = Document()
    doc.add_heading("Highlights", level=1)
    for l in lines:
        doc.add_paragraph(l, style="List Bullet")
    doc.save(OUT / "highlights.docx")
    shutil.copy(SUB / "highlights.txt", OUT / "highlights.txt")
    return lines


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "figures").mkdir(parents=True)
    (OUT / "tables").mkdir()
    (OUT / "generated").mkdir()
    checks = []
    order, ok_order, numbered = figure_order()
    checks.append(f"figures in order of first citation: {'yes' if ok_order else 'NO (numbering ' + str(numbered) + ')'}")
    ren = {}
    for i, (lab, f) in enumerate(order, 1):
        src = ROOT / "figures" / f"{f}.pdf"
        shutil.copy(src, OUT / "figures" / f"Figure_{i}.pdf")
        ren[f] = f"Figure_{i}"
        checks.append(f"  Figure_{i}.pdf <- figures/{f}.pdf ({lab})")
    for s in SOURCES:
        t = (PAPER / f"{s}.tex").read_text()
        for f, n in ren.items():
            t = re.sub(r"(\\includegraphics(?:\[[^\]]*\])?\{)" + re.escape(f) + r"\}", r"\g<1>" + n + "}", t)
        t = t.replace(r"\graphicspath{{figures/}{../figures/}}", r"\graphicspath{{figures/}}")
        (OUT / f"{s}.tex").write_text(t)
    shutil.copy(PAPER / "refs.bib", OUT / "refs.bib")
    shutil.copy(PAPER / "generated/numbers.tex", OUT / "generated/numbers.tex")
    vert = []
    for t in sorted((ROOT / "results/tables").glob("*.tex")):
        shutil.copy(t, OUT / "tables" / t.name)
        if re.search(r"\\begin\{tabular\}\{[^}]*\|", t.read_text()):
            vert.append(t.name)
    checks.append(f"tables with vertical rules: {vert or 'none'}")
    hl = highlights()
    checks.append(f"highlights: {len(hl)} bullets, max {max(len(l) for l in hl)} characters (limit 85)")
    checks.append(f"abstract: {abstract_words()} words (limit 250)")
    shutil.copy(SUB / "cover_letter.tex", OUT / "cover_letter.tex")
    for name in ("main", "cover_letter"):
        r = subprocess.run(["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", f"{name}.tex"], cwd=OUT,
                           capture_output=True, text=True)
        checks.append(f"{name}.tex compiles: {'yes' if r.returncode == 0 else 'NO'}")
    log = (OUT / "main.log").read_text(errors="ignore")
    und = sorted(set(re.findall(r"Reference `([^']+)' on page", log)))
    checks.append(f"undefined references: {und or 'none'}")
    pages = subprocess.run(["pdfinfo", "cover_letter.pdf"], cwd=OUT, capture_output=True, text=True).stdout
    checks.append("cover letter pages: " + (re.search(r"Pages:\s+(\d+)", pages).group(1) if "Pages" in pages else "?"))
    subprocess.run(["latexmk", "-c"], cwd=OUT, capture_output=True)
    for ext in ("fdb_latexmk", "fls", "log", "aux", "out", "blg"):
        for p in OUT.glob(f"*.{ext}"):
            p.unlink()
    (OUT / "CHECKS.txt").write_text("\n".join(checks) + "\n")
    print("\n".join(checks))
    return 0 if ok_order and not vert and not und else 1


if __name__ == "__main__":
    sys.exit(main())
