# Reference status (paper/refs.bib)

Journal names are abbreviated (LTWA) in refs.bib; DOIs are given wherever one was seen. Entries without
a DOI: bizic2021 (none found), harris2006 and johnson1985 (books, ISBN given), iso3095 (standard),
chaar2007 (thesis, ISBN), lebelhal (conference paper, HAL id).

No publisher page could be opened from this environment (WebFetch DNS failures; proxy 403), so
"confirmed" below means seen in web-search results (title/URL/summary of the named page), not read on
the publisher page. Check each DOI resolves before submission.

| Key | Status | Open points |
|---|---|---|
| carrigan2023 | full text in repo (docs/, gitignored) | – |
| sykulski2019 | confirmed (publisher listing) | – |
| whittle1953 | DOI seen in search | – |
| au2011 | DOI seen in search | – |
| friedman1993 | DOI, volume, pages seen (ScienceDirect, ADS) | given names not seen |
| cowper1966 | DOI seen (citedrive), 33(2) 335–340 in a reference list | given names not seen |
| harris2006 | 5th ed., 2 vols, ISBNs seen (booksellers) | – |
| iso3095 | 2013 edition cited (source of the roughness limit used); withdrawn, superseded by ISO 3095:2025 (ed. 4, 2025-09-11) | decide whether to cite 2025 as well |
| shen2023 | DOI seen; content per the user's full-text reading | – |
| liu2024 | DOI seen; surnames and initials from search | – |
| an2024 | title and authors (X. An, J. Hou, Q. Zhang, Z. Duan) seen in a citing reference list; DOI seen in round 1 | topic is vehicle parameters with unknown road excitation (Bayesian), as cited |
| guo2026 | title, five authors, vol 2026(1) art. 9457380 seen (Wiley page summary) | – |
| lebel2019 | title, JSV 458:158–176, DOI seen | – |
| lebelhal | hal-01876763 (Railways 2018, Barcelona) chosen as the HAL statistical-inverse paper; hal-01876753 is the WCCM Bayesian-calibration variant | proceedings publisher and pages not seen |
| jin2021 | DOI, volume, article number seen (ScienceDirect) | – |
| thompson2007 | title, 68(1) 43–57, DOI seen (Southampton ePrints) | removed 19 Oct 2026 (not verified by the full-text check; no longer cited) |
| dusza2023 | title, DOI seen; 1017/2280 kN/m empty/loaded seen | per axlebox vs per spring set |
| dusza2024 | title, 14(11) 4545, DOI seen (MDPI/DOAJ) | axlebox 100 kg seen in preprint table only |
| bizic2021 | venue Mechanics Transport Communications 19(3) art. 2113 | page numbers |
| guan2023 | title, authors (Tiantian Guan, Xiaoyu Deng, Jiangwen Wang), DOI seen | – |
| chaar2007 | thesis, TRITA AVE 2007:17, ISBN 978-91-7178-636-4 | – |
| randall2011 | 25(2) 485–520, DOI seen in two independent reference lists | – |
| pieringer2022 | Appl. Acoust. 193, 108760, DOI, authors seen (Chalmers repository record and full-text PDF listing) | – |
| johnson1985 | Contact Mechanics, CUP 1985, ISBN 0521255767 seen in library catalogues | DOI (Cambridge Core) not confirmed, so not given |
| hasan2020 | ICTD 2020, ASCE, DOI seen | removed 19 Oct 2026 (not verified by the full-text check; no longer cited) |
| li2026s2pinn | title, authors, arXiv:2610.03303 read from the PDF in docs/ (not committed) | – |
| nielsen2015 | title, 3(1) 17–39 seen (RePEc); author order differs between listings; DOI from round-1 snippet only | first-author order, DOI |

## The 10 most influential parameter sources still verified only from search snippets

Ranked by their effect on the results (model-form sensitivity, Table 6; sweep, Table 15; health case).
Dusza et al. 2024 (vehicle set) is full-text verified and not listed.

| # | Parameter (value used) | Why it matters | Source to check in full text |
|---|---|---|---|
| 1 | Wheel mass 304 kg (920 mm ER7) | unsprung mass is the largest model-form term | Unirail BA004 wheelset datasheet (unirail.bg) |
| 2 | Axle diameters 130/200/173 mm, length 2180 mm | axle mass (397 kg) and bending modes | BA004 / Unirail listings; EN 13261 axle drawing |
| 3 | Rail pad stiffness 200 MN/m per pad | sets k_f, second-largest model-form term | Thompson, Jones, Waters & Farrington (2007), Appl. Acoust. 68(1) 43–57 |
| 4 | Sleeper spacing 0.60 m | sets k_f | EUROBOLT optimal-track chapter (Nova); CT23 Table 1 |
| 5 | Foundation loss factor 0.2 (0.1–0.25) | rail receptance damping, coupling | Thompson et al. (2007) pad table; rolling-noise model papers |
| 6 | Eanos bogie pivot pitch 10.70 m, length over buffers 15.74 m; Y25 wheelbase 1.80 m | wheel layout, coupling phase factors | Rail Cargo Group Eanos fact sheet; Wascosa Eanos 82.5 datasheet; railway-technology.com Y25 |
| 7 | Y25 bearing type WJ/WJP 130×240 and radial clearance 130–180 µm | main health case | SKF Railway Technical Handbook vol. 1 (cylindrical roller bearings, DIN 5412-11); Schaeffler TPI 256 |
| 8 | UIC60 crown radius 0.30 m | k_H0 from Hertz | EN 13674-1 60E1 profile drawing |
| 9 | 60E1 section A = 76.70 cm², I = 3038.3 cm⁴ | rail receptance | ArcelorMittal / British Steel 60E1 datasheets (EN 13674-1) |
| 10 | Wheelset modal damping < 2% (first torsion and bending) | axle damping; swept 0.1–2% | Chaar (2007), KTH thesis TRITA AVE 2007:17, Table 2-1 |

## Added 2026-10-17 (novelty table), unverified

| Key | Full reference | Status |
|---|---|---|
| li2019axlebox | Li, T., Sun, W., Meng, Z., Huo, J., Dong, J., Wang, L. (2019). Dynamic investigation on railway vehicle considering the dynamic effect from the axle box bearings. *Advances in Mechanical Engineering* 11(4), 1–13. doi:10.1177/1687814019840503 | DOI, authors and year from a DOAJ listing and a citing reference list (search snippets); full text not read |
