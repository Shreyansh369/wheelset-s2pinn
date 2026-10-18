"""docs/reference_check.md: every reference of the paper, in citation order, with its DOI (or ISBN/URL)
and a blank "checked by author" column for hand verification before submission.
Order and numbering come from paper/main.bbl (run `make -C paper` first); fields from paper/refs.bib.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def parse_bib(text):
    out = {}
    for m in re.finditer(r"@(\w+)\{([^,]+),(.*?)\n\}", text, re.S):
        fields = dict((k.lower(), re.sub(r"\s+", " ", v).strip())
                      for k, v in re.findall(r"(\w+)\s*=\s*\{((?:[^{}]|\{[^{}]*\})*)\}", m.group(3)))
        out[m.group(2).strip()] = {"type": m.group(1).lower(), **fields}
    return out


def clean(s):
    s = re.sub(r"\\[\"'`^~v]\{?(\w)\}?", r"\1", s)
    s = s.replace("---", "—")
    return s.replace("{", "").replace("}", "").replace("\\&", "&").replace("--", "–").replace("$^2$", "²")


UNVERIFIED_NEW = {  # entries added after the search-based status check; to be verified by hand
    "li2019axlebox": "c_B 6740 N s/m and the TRB geometry in Table 3 verified by full-text fetch 19 Oct 2026; volume/issue 11(4), April 2019 (DOAJ)",
    "bizic2024": "Table 1 source, content verified by full-text fetch 19 Oct 2026; title per the authors' check; DOI 10.12700/APH.21.1.2024.1.10 confirmed in the scidar.kg.ac.rs repository metadata",
    "jin2016": "Table 1 source, content verified by full-text fetch 19 Oct 2026 (via Ahmedov & Mirsaidov 2023); title and authors per the authors' check",
    "ahmedov2023": "Table 1 source, content verified by full-text fetch 19 Oct 2026; title and pages from a search result: check",
    "han2025": "Table 1 source, content verified by full-text fetch 19 Oct 2026; authors per the authors' check",
    "knuth2025": "Table 1 source, content verified by full-text fetch 19 Oct 2026; title from a search result: check",
    "deman2000": "Table 1 source, content verified by full-text fetch 19 Oct 2026; title per the authors' check; pages not known",
    "thompson_eprint436918": "Table 1 source, content verified by full-text fetch 19 Oct 2026; accepted manuscript, journal version and year not known: check",
    "jones1996": "Table 1 source, content verified by full-text fetch 19 Oct 2026; title from the IOA proceedings file name: check",
    "sanudo2022": "Table 1 source, content verified by full-text fetch 19 Oct 2026; title and authors per the authors' check",
    "unirail_ba004": "Table 1 source, content verified by full-text fetch 19 Oct 2026; vendor datasheet",
    "interpipe_axles": "Table 1 source, content verified by full-text fetch 19 Oct 2026",
    "railwayspares_ba004": "Table 1 source, content verified by full-text fetch 19 Oct 2026; vendor listing",
    "skf_rth2012": "Table 1 source, content verified by full-text fetch 19 Oct 2026; extract of ch. 4, p. 89 (c) SKF 2012; full title from a search result: check",
    "schaeffler_wl07519": "Table 1 source, content verified by full-text fetch 19 Oct 2026; add year",
    "skf_evol2005": "Table 1 source, content verified by full-text fetch 19 Oct 2026",
    "skf_evol2022": "Table 1 source, content verified by full-text fetch 19 Oct 2026; title per the authors' check",
    "tatravagonka_y25": "Table 1 source, content verified by full-text fetch 19 Oct 2026",
    "wascosa_eanos": "Table 1 source, content verified by full-text fetch 19 Oct 2026",
    "railcargo_eanos": "Table 1 source, content verified by full-text fetch 19 Oct 2026; add year",
    "tstg_rails": "Table 1 source, content verified by full-text fetch 19 Oct 2026; catalogue title from a search result: check",
    "britishsteel_rails": "Table 1 source, content verified by full-text fetch 19 Oct 2026",
}


def main():
    bib = parse_bib((ROOT / "paper/refs.bib").read_text())
    order = re.findall(r"\\bibitem\{([^}]+)\}", (ROOT / "paper/main.bbl").read_text())
    rows = []
    for i, k in enumerate(order, 1):
        e = bib[k]
        authors = clean(e.get("author", ""))
        a = authors.split(" and ")
        who = a[0].split(",")[0] + (" et al." if len(a) > 2 else (" & " + a[1].split(",")[0] if len(a) == 2 else ""))
        venue = clean(e.get("journal") or e.get("booktitle") or e.get("publisher") or e.get("school") or e.get("howpublished", ""))
        vol = e.get("volume", "") + (f"({e['number']})" if e.get("number") else "")
        vol = ", ".join(x for x in (vol, clean(e.get("pages", ""))) if x)
        if e.get("doi"):
            ident = f"doi: [{e['doi']}](https://doi.org/{e['doi']})"
        elif e.get("isbn"):
            ident = f"ISBN {e['isbn']}"
        elif e.get("url"):
            ident = e["url"]
        else:
            ident = clean(e.get("note", "")) or "none found"
        flag = f" **{UNVERIFIED_NEW[k]}**" if k in UNVERIFIED_NEW else ""
        rows.append(f"| [{i}] | `{k}` | {who} ({e.get('year', '')}). {clean(e.get('title', ''))}. *{venue}* {vol}{flag} | {ident} | |")
    hdr = ("# Reference check\n\nEvery reference of the manuscript in citation order (numbering of `paper/main.bbl`), with the "
           "identifier to check it against. Fill the last column by hand after checking author list, title, venue, volume, "
           "pages and year against the publisher's page. Search-based status of each entry: `docs/reference_status.md`. "
           "Regenerate with `python3 experiments/make_reference_check.py` after `make -C paper`.\n\n"
           "| # | Key | Reference | DOI / ISBN / URL | Checked by author (initials, date) |\n|---|---|---|---|---|\n")
    unused = sorted(set(bib) - set(order))
    tail = f"\nEntries in refs.bib not cited in the manuscript (not printed): {', '.join(f'`{u}`' for u in unused) or 'none'}.\n"
    (ROOT / "docs/reference_check.md").write_text(hdr + "\n".join(rows) + "\n" + tail)
    print(f"{len(rows)} references, {len(unused)} uncited")


if __name__ == "__main__":
    main()
