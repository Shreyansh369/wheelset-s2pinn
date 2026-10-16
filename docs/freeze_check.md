# Freeze cross-check

Every number in the abstract, highlights, conclusions and cover letter, with the generated value, the result file it comes from and the configuration it was computed with. Regenerate with `python3 experiments/make_freeze_check.py` after `make_paper_numbers.py`.

## paper/abstract.tex

| Macro | Value | Source | Configuration |
|---|---|---|---|
| `\HLBiasAbsMax` | 0.07 | results/p3/headline_v2_kb120_attr_freight.json | current wagon, but k_H0 1.4 GN/m and c_p 10 kN s/m (pinned headline config) |
| `\HLRMSEMin` | 0.19 | results/p3/headline_v2_kb120_attr_freight.json | current wagon, but k_H0 1.4 GN/m and c_p 10 kN s/m (pinned headline config) |
| `\HLRMSEMax` | 0.20 | results/p3/headline_v2_kb120_attr_freight.json | current wagon, but k_H0 1.4 GN/m and c_p 10 kN s/m (pinned headline config) |
| `\HLRatioCRBMax` | 1.08 | results/p3/headline_v2_kb120_attr_freight.json | current wagon, but k_H0 1.4 GN/m and c_p 10 kN s/m (pinned headline config) |
| `\IgnoreCouplingForty` | -5.6 | results/p4/ignore_coupling.json | current (representative wagon, Table 1) |
| `\ICDiffMean` | 0.059 | results/p4/inverse_crime.json | current (representative wagon, Table 1) |
| `\BudgetCoest` | 10.0 | results/p2/model_form_mw_sensitivity.json | current (representative wagon, Table 1) |
| `\BandEmptyMDCFiftyMin` | 0.75 | results/p4/banded.json | current (representative wagon, Table 1); payload bands |
| `\BandEmptyMDCFiftyMax` | 0.83 | results/p4/banded.json | current (representative wagon, Table 1); payload bands |
| `\BandEmptyMDCTwoHundredMin` | 0.35 | results/p4/banded.json | current (representative wagon, Table 1); payload bands |
| `\BandEmptyMDCTwoHundredMax` | 0.39 | results/p4/banded.json | current (representative wagon, Table 1); payload bands |
| `\EffPctTenEmpty` | -0.74 | results/p3/bearing_clearance.json | current (representative wagon, Table 1) |

## paper/sec6_conclusions.tex

| Macro | Value | Source | Configuration |
|---|---|---|---|
| `\HLBiasAbsMax` | 0.07 | results/p3/headline_v2_kb120_attr_freight.json | current wagon, but k_H0 1.4 GN/m and c_p 10 kN s/m (pinned headline config) |
| `\HLRMSEMin` | 0.19 | results/p3/headline_v2_kb120_attr_freight.json | current wagon, but k_H0 1.4 GN/m and c_p 10 kN s/m (pinned headline config) |
| `\HLRMSEMax` | 0.20 | results/p3/headline_v2_kb120_attr_freight.json | current wagon, but k_H0 1.4 GN/m and c_p 10 kN s/m (pinned headline config) |
| `\HLRatioCRBMax` | 1.08 | results/p3/headline_v2_kb120_attr_freight.json | current wagon, but k_H0 1.4 GN/m and c_p 10 kN s/m (pinned headline config) |
| `\IgnoreCouplingForty` | -5.6 | results/p4/ignore_coupling.json | current (representative wagon, Table 1) |
| `\ICDiffMean` | 0.059 | results/p4/inverse_crime.json | current (representative wagon, Table 1) |
| `\BudgetCoest` | 10.0 | results/p2/model_form_mw_sensitivity.json | current (representative wagon, Table 1) |
| `\BandEmptyMDCFiftyMin` | 0.75 | results/p4/banded.json | current (representative wagon, Table 1); payload bands |
| `\BandEmptyMDCFiftyMax` | 0.83 | results/p4/banded.json | current (representative wagon, Table 1); payload bands |

## Numbers typed by hand (highlights, cover letter)

| File | Typed | Macro | Macro value | Match |
|---|---|---|---|---|
| paper/submission/highlights.txt | 5.6% | `\IgnoreCouplingForty` | -5.6 | yes |
| paper/submission/cover_letter.tex | 5.6\% | `\IgnoreCouplingForty` | -5.6 | yes |

## Numbers from an older configuration

- none in the abstract or conclusions

Other numbers in these texts are design values (50/200 passes, 60–110 km/h, 20/40 dB, 22.5 t, 10 µm, 20 %), not results.
