"""Task (a): wheel-to-wheel coupling through the rail (Carrigan & Talbot 2023, Eqs. 5-11), cross terms kept.

Track: infinite Timoshenko rail (BS113A, CT23 Table 1) on a continuous hysteretic foundation,
kf = 154 MN/m^2, eta_f = 0.2 ("standard track", CT23 Sec. 5.1.1). Wheel layout: CT23 Fig. 5
(2009-stock); instrumented wheel d5; subsets of 2, 4 and 8 wheels as in CT23 Fig. 9. Every wheelset
is the repo's FE wheelset at the same payload; only the instrumented one has the bearing under test
(kB0, cB); the others are nominal (1e9 N/m, 5e3 N s/m). Roughness: same profile under all wheels
(shifted by the wheel spacing) and on both rails, ISO 3095 shape, K = 16 free sub-band levels.

--bound: expected-Fisher kB0/cB bounds for 1, 2, 4, 8 wheels x speeds (fixed 100 / 95-105 / 60-110)
         at N = 50, SNR 40 dB, plus the 60E1 rail at 60-110 km/h (sensitivity).
--mc:    20 datasets per wheel count (2, 4, 8) at 60-110 km/h, N = 50, SNR 40 dB, fitted with
         (i) the correct rail-coupled model and (ii) the single-wheelset model on the same rail
         (mismatched-model test).
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

from experiments.p1_fe_direct import G_SD_DB, START, TRUTH, WIM, W_RANGE, Z90, cp_interval, setup  # noqa: E402
from src.analysis.multiwheel import MultiWheelFamily, MultiWheelModel  # noqa: E402
from src.inverse.multipass import MultiPassWhittle, generate_pass  # noqa: E402
from src.reference.track import load_track_config, make_track  # noqa: E402
from src.utils.results import RESULTS_DIR, Timer, save_result  # noqa: E402

KMH = 1 / 3.6
SPEEDS = {"fixed_100": (100.0, 100.0), "uniform_95_105": (95.0, 105.0), "uniform_60_110": (60.0, 110.0)}
FG = np.arange(44.0, 701.0, 0.25)
RUN_DIR = RESULTS_DIR / "p2" / "multiwheel_runs"


def models(sm, rail="BS113A"):
    cfg = load_track_config()
    track = make_track(rail, cfg=cfg)
    pos = np.array(cfg["layout_CT23"]["positions"])
    j0 = int(cfg["layout_CT23"]["instrumented_index"])
    subsets = {"1": [j0], **cfg["layout_CT23"]["subsets"]}
    out = {}
    for nm, idx in subsets.items():
        out[nm] = MultiWheelModel(sm, track, pos[idx], list(idx).index(j0))
    return out, track


def dataset(sm, thb, rough, mw: MultiWheelModel, seed_key, N=50, snr=40.0, speeds=(60.0, 110.0), g_sd=G_SD_DB):
    rng = np.random.default_rng(np.random.SeedSequence(seed_key))
    g = 10 ** (rng.normal(0, g_sd, rough.n_sub) / 10)
    Vs = rng.uniform(*speeds, N) * KMH
    Ws = rng.uniform(*W_RANGE, N)
    th = dict(thb, **TRUTH)
    passes = [generate_pass(mw.reference_H(dict(th, W=float(W)), V, FG), rough, g, V, thb["r0"], snr, rng)
              for V, W in zip(Vs, Ws)]
    Wm = Ws * np.exp(WIM * rng.standard_normal(N))
    return passes, Wm, Ws, g


def bound(args):
    sm, thb, rough, _ = setup()
    rows = []
    with Timer() as tm:
        for rail in ("BS113A", "60E1"):
            mws, track = models(sm, rail)
            for nw, mw in mws.items():
                fam = MultiWheelFamily(mw, thb)
                for sname, spd in SPEEDS.items():
                    if rail == "60E1" and sname != "uniform_60_110":
                        continue
                    passes, Wm, Ws, g = dataset(sm, thb, rough, mw, (20261012, 99, int(nw)), speeds=spd, g_sd=0.0)
                    est = MultiPassWhittle(passes, Ws, WIM, rough, fam)
                    c = est.expected_fisher(np.log([TRUTH["kB0"], TRUTH["cB"]]), np.log(g), np.log(Ws))
                    rows.append({"rail": rail, "wheels": int(nw), "speeds": sname, "N": 50, "snr_db": 40.0,
                                 "crb_rel_kB0": c["crb_log"][0], "crb_rel_cB": c["crb_log"][1], "track": track.__dict__})
                    print(rows[-1]["rail"], nw, sname, round(c["crb_log"][0] * 100, 3), round(c["crb_log"][1] * 100, 2), flush=True)
    save_result("p2/multiwheel_bound", {"rows": rows}, cfg={
        "layout": "CT23 Fig. 5 subsets", "foundation": "kf 154 MN/m^2, eta_f 0.2 (CT23 Sec. 5.1.1)",
        "neighbour_bearing": "kB0 1e9, cB 5e3", "truth": TRUTH, "wim_sigma": WIM, "roughness": "ISO 3095 shape, K=16 levels free"},
        seed=20261012, wall_seconds=tm.seconds)


def mc(args):
    sm, thb, rough, _ = setup()
    mws, _ = models(sm)
    fam_single = MultiWheelFamily(mws["1"], thb)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    for nw in args.wheels:
        mw = mws[str(nw)]
        fam = MultiWheelFamily(mw, thb)
        fp = RUN_DIR / f"wheels{nw}_{args.speeds}.jsonl"
        done = {tuple(json.loads(l)["seed_key"]) for l in fp.read_text().splitlines()} if fp.exists() else set()
        for j in range(args.n_data):
            key = (args.seed_base, nw, j)
            if key in done:
                continue
            t0 = time.perf_counter()
            passes, Wm, Ws, g = dataset(sm, thb, rough, mw, key, speeds=SPEEDS[args.speeds])
            t_gen = time.perf_counter() - t0
            row = {"wheels": nw, "speeds": args.speeds, "seed_key": list(key), "wall_generate_s": t_gen}
            for tag, fm in (("correct", fam), ("single_wheelset", fam_single)):
                est = MultiPassWhittle([dict(q) for q in passes], Wm, WIM, rough, fm)
                r = est.fit(np.log([START["kB0"], START["cB"]]))
                pi = est.profile_interval(0) if tag == "correct" else None
                crb = est.expected_fisher(np.log([TRUTH["kB0"], TRUTH["cB"]]), np.log(g), np.log(Ws)) if tag == "correct" else None
                row[tag] = {"phi_hat": r["phi"], "se_log": r["se_log"], "converged": r["converged"],
                            "err_log": [r["phi"][0] - math.log(TRUTH["kB0"]), r["phi"][1] - math.log(TRUTH["cB"])],
                            "wall_fit_s": r["wall_fit_s"], "s_per_eval": r["s_per_eval"],
                            "profile90": pi, "crb_log": crb["crb_log"] if crb else None}
            with fp.open("a") as fh:
                fh.write(json.dumps(row) + "\n")
            print(f"wheels={nw} j={j} correct err={row['correct']['err_log'][0]:+.4f} se={row['correct']['se_log'][0]:.4f} "
                  f"| single err={row['single_wheelset']['err_log'][0]:+.4f} fit={row['correct']['wall_fit_s']:.0f}s", flush=True)


def aggregate(args):
    cells = []
    for fp in sorted(RUN_DIR.glob("*.jsonl")):
        rows = [json.loads(l) for l in fp.read_text().splitlines() if l.strip()]
        crb = np.array([r["correct"]["crb_log"][0] for r in rows])
        cell = {"file": fp.name, "wheels": rows[0]["wheels"], "speeds": rows[0]["speeds"], "n": len(rows),
                "crb_rel_kB0": float(np.sqrt(np.mean(crb**2)))}
        for tag in ("correct", "single_wheelset"):
            e = np.array([r[tag]["err_log"][0] for r in rows])
            se = np.array([r[tag]["se_log"][0] for r in rows])
            k = int(np.sum(np.abs(e) <= Z90 * se))
            cell[tag] = {"bias_rel_kB0": float(np.mean(np.exp(e) - 1)),
                         "bias_rel_kB0_se": float(np.std(np.exp(e) - 1, ddof=1) / math.sqrt(len(e))),
                         "rmse_rel_kB0": float(np.sqrt(np.mean(e**2))),
                         "rmse_over_crb": float(np.sqrt(np.mean(e**2)) / cell["crb_rel_kB0"]),
                         "coverage90_wald": k / len(e), "coverage90_wald_ci95": cp_interval(k, len(e)),
                         "all_converged": all(r[tag]["converged"] for r in rows),
                         "fit_s_median": float(np.median([r[tag]["wall_fit_s"] for r in rows]))}
        lo = np.array([r["correct"]["profile90"]["lo"] for r in rows])
        hi = np.array([r["correct"]["profile90"]["hi"] for r in rows])
        kp = int(np.sum((lo <= math.log(TRUTH["kB0"])) & (hi >= math.log(TRUTH["kB0"]))))
        cell["correct"]["coverage90_profile"] = kp / len(rows)
        cell["correct"]["coverage90_profile_ci95"] = cp_interval(kp, len(rows))
        cells.append(cell)
        print(json.dumps(cell), flush=True)
    save_result("p2/multiwheel_mc", {"cells": cells}, cfg={"truth": TRUTH, "N": 50, "snr_db": 40, "wim_sigma": WIM,
                                                          "track": "BS113A, kf 154 MN/m^2, eta 0.2", "layout": "CT23"},
                seed=20261012)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--bound", action="store_true")
    ap.add_argument("--mc", action="store_true")
    ap.add_argument("--aggregate", action="store_true")
    ap.add_argument("--wheels", type=int, nargs="+", default=[2, 4, 8])
    ap.add_argument("--speeds", default="uniform_60_110")
    ap.add_argument("--n-data", type=int, default=20)
    ap.add_argument("--seed-base", type=int, default=20261012)
    a = ap.parse_args()
    if a.bound:
        bound(a)
    if a.mc:
        mc(a)
    if a.aggregate:
        aggregate(a)
