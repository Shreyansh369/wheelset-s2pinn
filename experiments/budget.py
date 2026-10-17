"""Absolute bias budget of k_B0 at the current configuration (one definition for tables and macros).

From results/p2/model_form_mw_sensitivity.json: root sum of squares of the worst-side 1-sigma pseudo-true
biases of the uncertain model parameters, for the nominal fit and with k_f, k_H0 co-estimated; the
"mass known to 1%" variant scales the unsprung-mass term linearly from its 1-sigma range to 1%.
"""

import math


def budget(d):
    sig_m = d["ranges"]["unsprung_scale"][0] if isinstance(d["ranges"]["unsprung_scale"], list) else d["ranges"]["unsprung_scale"]
    out = {"mass_sigma_pct": 100 * sig_m}
    for e in ("nominal", "coest"):
        t = dict(d["budget"][e]["terms_pct_1sigma_worst_side"])
        t1 = dict(t, unsprung_scale=t["unsprung_scale"] * 0.01 / sig_m)
        out[e] = {"rss_pct": d["budget"][e]["rss_pct"], "rss_mass1_pct": math.sqrt(sum(v**2 for v in t1.values()))}
    return out
