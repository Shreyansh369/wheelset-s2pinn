"""Phase 2 (2)+(3): five-seed headline numbers with Wald and profile-likelihood 90% intervals.

Headline cell: N = 50 passes, speeds uniform 60-110 km/h, payload measured (3% WIM), SNR 20 and
40 dB; seeds 42, 123, 456, 789, 1024, each a block of 20 random datasets. Per dataset: ML fit of
(kB0, cB), Wald SE from the observed profile information, 90% profile-likelihood interval for kB0
(cB and all nuisances re-optimised), expected-Fisher CRB at the truth.
Rows: results/p2/headline_runs/snr<snr>_seed<seed>.jsonl; --aggregate -> results/p2/headline.json.
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

from experiments.p2_common import SEEDS, TRUTH, WIM, make_dataset, phi_start, phi_true, setup, summarise  # noqa: E402
from src.inverse.multipass import MultiPassWhittle, SingleWheelsetFamily  # noqa: E402
from src.utils.results import RESULTS_DIR, save_result  # noqa: E402

RUN_DIR = RESULTS_DIR / "p2" / "headline_runs"


def run_dir(fit_noise=False, debias=False):
    return RESULTS_DIR / "p2" / ("headline_runs" + ("_noisefit" if fit_noise else "") + ("_debias" if debias else ""))


def run(snrs, seeds, n_data, fit_noise=False, debias=False):
    global RUN_DIR
    RUN_DIR = run_dir(fit_noise, debias)
    sm, thb, rough, _ = setup()
    fam = SingleWheelsetFamily(sm, thb)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    for snr in snrs:
        for seed in seeds:
            fp = RUN_DIR / f"snr{int(snr)}_seed{seed}.jsonl"
            done = {tuple(json.loads(l)["seed_key"]) for l in fp.read_text().splitlines()} if fp.exists() else set()
            for j in range(n_data):
                key = (seed, int(snr), j)
                if key in done:
                    continue
                t0 = time.perf_counter()
                ds = make_dataset(sm, thb, rough, key, snr=snr)
                t_gen = time.perf_counter() - t0
                est = MultiPassWhittle(ds["passes"], ds["Wm"], WIM, rough, fam, fit_noise=fit_noise, debias=debias)
                r = est.fit(phi_start())
                t1 = time.perf_counter()
                pi = est.profile_interval(0)
                t_pi = time.perf_counter() - t1
                crb = est.expected_fisher(phi_true(), np.log(ds["g"]), np.log(ds["Ws"]))
                lt = math.log(TRUTH["kB0"])
                row = {"snr_db": snr, "seed": seed, "seed_key": list(key), "phi_hat": r["phi"], "se_log": r["se_log"],
                       "err_log": [r["phi"][0] - lt, r["phi"][1] - math.log(TRUTH["cB"])],
                       "profile90_err": [pi["lo"] - lt, pi["hi"] - lt], "profile_n_eval": pi["n_eval"],
                       "crb_log": crb["crb_log"], "converged": r["converged"], "wall_fit_s": r["wall_fit_s"],
                       "s_per_eval": r["s_per_eval"], "wall_profile_s": t_pi, "wall_generate_s": t_gen}
                with fp.open("a") as fh:
                    fh.write(json.dumps(row) + "\n")
                print(f"snr={snr} seed={seed} j={j} err={row['err_log'][0]:+.4f} se={r['se_log'][0]:.4f} "
                      f"prof=[{row['profile90_err'][0]:+.4f},{row['profile90_err'][1]:+.4f}] fit={r['wall_fit_s']:.0f}s "
                      f"prof={t_pi:.0f}s", flush=True)


def aggregate(fit_noise=False, debias=False):
    global RUN_DIR
    RUN_DIR = run_dir(fit_noise, debias)
    out = []
    for snr in (20, 40):
        per_seed = []
        allrows = []
        for seed in SEEDS:
            fp = RUN_DIR / f"snr{snr}_seed{seed}.jsonl"
            if not fp.exists():
                continue
            rows = [json.loads(l) for l in fp.read_text().splitlines() if l.strip()]
            allrows += rows
            s = summarise([r["err_log"][0] for r in rows], [r["se_log"][0] for r in rows], [r["crb_log"][0] for r in rows],
                          profile=([r["profile90_err"][0] for r in rows], [r["profile90_err"][1] for r in rows]))
            per_seed.append({"seed": seed, **s})
        if not allrows:
            continue
        pooled = summarise([r["err_log"][0] for r in allrows], [r["se_log"][0] for r in allrows],
                           [r["crb_log"][0] for r in allrows],
                           profile=([r["profile90_err"][0] for r in allrows], [r["profile90_err"][1] for r in allrows]))
        across = {k: {"mean": float(np.mean([p[k] for p in per_seed])), "sd": float(np.std([p[k] for p in per_seed], ddof=1))}
                  for k in ("bias_rel", "rmse_rel", "crb_rel", "rmse_over_crb", "coverage90_wald", "coverage90_profile")}
        cB = summarise([r["err_log"][1] for r in allrows], [r["se_log"][1] for r in allrows], [r["crb_log"][1] for r in allrows])
        timing = {"s_per_eval_median": float(np.median([r["s_per_eval"] for r in allrows])),
                  "fit_s_median": float(np.median([r["wall_fit_s"] for r in allrows])),
                  "profile_s_median": float(np.median([r["wall_profile_s"] for r in allrows]))}
        out.append({"snr_db": snr, "kB0_per_seed": per_seed, "kB0_across_seeds": across, "kB0_pooled": pooled,
                    "cB_pooled": cB, "timing": timing, "all_converged": all(r["converged"] for r in allrows)})
        print(json.dumps(out[-1]["kB0_across_seeds"]), json.dumps(pooled), flush=True)
    save_result("p2/headline" + ("_noisefit" if fit_noise else "") + ("_debias" if debias else ""), {"cells": out}, cfg={"N": 50, "speeds_kmh": [60, 110], "wim_sigma": WIM, "seeds": SEEDS,
                                                    "datasets_per_seed": 20, "truth": TRUTH,
                                                    "intervals": "Wald (observed profile information) and profile likelihood, 90%",
                                                    "noise_floor": "profiled jointly (in-band + out-of-band bins)" if fit_noise else "plug-in out-of-band mean",
                                                    "likelihood": "debiased Whittle" if debias else "bin-sampled Whittle"},
                seed=SEEDS[0])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--snr", type=float, nargs="+", default=[20.0, 40.0])
    ap.add_argument("--seeds", type=int, nargs="+", default=list(SEEDS))
    ap.add_argument("--n-data", type=int, default=20)
    ap.add_argument("--aggregate", action="store_true")
    ap.add_argument("--fit-noise", action="store_true")
    ap.add_argument("--debias", action="store_true")
    a = ap.parse_args()
    aggregate(a.fit_noise, a.debias) if a.aggregate else run(a.snr, a.seeds, a.n_data, a.fit_noise, a.debias)
