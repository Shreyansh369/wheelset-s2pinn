"""Headline Monte Carlo on the final (rail-coupled) model.

Data: instrumented FE wheelset + 3 neighbours (CT23 4-wheel subset) on the BS113A Timoshenko rail with
a hysteretic foundation (kf 154 MN/m^2, eta_f 0.2), N = 50 passes, speeds uniform 60-110 km/h, payload
5.5-22.5 t with 3% WIM error, ISO 3095 roughness shape with K = 16 sub-band levels (3 dB deviations),
SNR 20 and 40 dB; seeds 42, 123, 456, 789, 1024, 10 datasets each.
Estimator: debiased Whittle with the rail-coupled model (kB0, cB free). Wald 90% intervals from the
observed profile information for all datasets; profile-likelihood intervals for seed 42 only (on the
single-wheelset benchmark profile and Wald intervals coincided, width ratio 0.9999).
"Ignore coupling": for seed 42 only, the same data fitted with the single-wheelset model on the same rail.
Rows: results/p2/headline_mw_runs/snr<snr>_seed<seed>.jsonl; --aggregate -> results/p2/headline_mw.json.
"""

from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "1"

import argparse  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.p2_common import SEEDS, START, TRUTH, WIM, setup, summarise  # noqa: E402
from experiments.p2_multiwheel import dataset as mw_dataset, models  # noqa: E402
from src.analysis.multiwheel import MultiWheelFamily  # noqa: E402
from src.inverse.multipass import MultiPassWhittle  # noqa: E402
from src.utils.results import RESULTS_DIR, save_result  # noqa: E402

RUN_DIR = RESULTS_DIR / "p2" / "headline_mw_runs"
PHI0 = np.log([START["kB0"], START["cB"]])
PHIT = np.log([TRUTH["kB0"], TRUTH["cB"]])


def run(snrs, seeds, n_data):
    sm, thb, rough, _ = setup()
    mws, _ = models(sm)
    fam = MultiWheelFamily(mws["4"], thb)
    fam1 = MultiWheelFamily(mws["1"], thb)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    lt = math.log(TRUTH["kB0"])
    for snr in snrs:
        for seed in seeds:
            fp = RUN_DIR / f"snr{int(snr)}_seed{seed}.jsonl"
            done = {tuple(json.loads(l)["seed_key"]) for l in fp.read_text().splitlines()} if fp.exists() else set()
            for j in range(n_data):
                key = (seed, int(snr), j)
                if key in done:
                    continue
                t0 = time.perf_counter()
                P, Wm, Ws, g = mw_dataset(sm, thb, rough, mws["4"], key, N=50, snr=snr)
                t_gen = time.perf_counter() - t0
                est = MultiPassWhittle([dict(q) for q in P], Wm, WIM, rough, fam, debias=True)
                r = est.fit(PHI0)
                crb = est.expected_fisher(PHIT, np.log(g), np.log(Ws))["crb_log"]
                row = {"snr_db": snr, "seed": seed, "seed_key": list(key), "phi_hat": r["phi"], "se_log": r["se_log"],
                       "err_log": [r["phi"][0] - lt, r["phi"][1] - math.log(TRUTH["cB"])], "crb_log": crb,
                       "converged": r["converged"], "wall_fit_s": r["wall_fit_s"], "s_per_eval": r["s_per_eval"],
                       "wall_generate_s": t_gen}
                if seed == SEEDS[0]:
                    pi = est.profile_interval(0)
                    row["profile90_err"] = [pi["lo"] - lt, pi["hi"] - lt]
                    e1 = MultiPassWhittle([dict(q) for q in P], Wm, WIM, rough, fam1, debias=True)
                    r1 = e1.fit(PHI0)
                    row["ignore_coupling"] = {"err_log": r1["phi"][0] - lt, "se_log": r1["se_log"][0], "converged": r1["converged"]}
                with fp.open("a") as fh:
                    fh.write(json.dumps(row) + "\n")
                print(f"snr={snr} seed={seed} j={j} err={row['err_log'][0]:+.4f} se={r['se_log'][0]:.4f} crb={crb[0]:.4f} "
                      f"fit={r['wall_fit_s']:.0f}s", flush=True)


def aggregate():
    out = []
    for snr in (20, 40):
        per_seed, allrows = [], []
        for seed in SEEDS:
            fp = RUN_DIR / f"snr{snr}_seed{seed}.jsonl"
            if not fp.exists():
                continue
            rows = [json.loads(l) for l in fp.read_text().splitlines() if l.strip()]
            allrows += rows
            per_seed.append({"seed": seed, **summarise([r["err_log"][0] for r in rows], [r["se_log"][0] for r in rows],
                                                       [r["crb_log"][0] for r in rows])})
        if not allrows:
            continue
        pooled = summarise([r["err_log"][0] for r in allrows], [r["se_log"][0] for r in allrows], [r["crb_log"][0] for r in allrows])
        across = {k: {"mean": float(np.mean([p[k] for p in per_seed])),
                      "sd": float(np.std([p[k] for p in per_seed], ddof=1)) if len(per_seed) > 1 else None}
                  for k in ("bias_rel", "rmse_rel", "crb_rel", "rmse_over_crb", "coverage90_wald")}
        sub = [r for r in allrows if "profile90_err" in r]
        prof = summarise([r["err_log"][0] for r in sub], [r["se_log"][0] for r in sub], [r["crb_log"][0] for r in sub],
                         profile=([r["profile90_err"][0] for r in sub], [r["profile90_err"][1] for r in sub])) if sub else None
        ign = summarise([r["ignore_coupling"]["err_log"] for r in sub], [r["ignore_coupling"]["se_log"] for r in sub],
                        [r["crb_log"][0] for r in sub]) if sub else None
        cB = summarise([r["err_log"][1] for r in allrows], [r["se_log"][1] for r in allrows], [r["crb_log"][1] for r in allrows])
        out.append({"snr_db": snr, "kB0_per_seed": per_seed, "kB0_across_seeds": across, "kB0_pooled": pooled,
                    "kB0_seed42_with_profile": prof, "ignore_coupling_seed42": ign, "cB_pooled": cB,
                    "fit_s_median": float(np.median([r["wall_fit_s"] for r in allrows])),
                    "all_converged": all(r["converged"] for r in allrows)})
        print(json.dumps({k: v for k, v in out[-1].items() if k != "kB0_per_seed"}), flush=True)
    save_result("p2/headline_mw", {"cells": out}, cfg={
        "model": "4-wheel rail-coupled (CT23 subset), BS113A Timoshenko rail, kf 154e6, eta_f 0.2", "likelihood": "debiased Whittle",
        "N": 50, "speeds_kmh": [60, 110], "wim_sigma": WIM, "seeds": SEEDS, "datasets_per_seed": 10, "truth": TRUTH},
        seed=SEEDS[0])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--snr", type=float, nargs="+", default=[20.0, 40.0])
    ap.add_argument("--seeds", type=int, nargs="+", default=list(SEEDS))
    ap.add_argument("--n-data", type=int, default=10)
    ap.add_argument("--aggregate", action="store_true")
    a = ap.parse_args()
    aggregate() if a.aggregate else run(a.snr, a.seeds, a.n_data)
