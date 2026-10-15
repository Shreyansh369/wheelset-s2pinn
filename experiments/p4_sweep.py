"""Sweep of the bound and detection limit over the published (or assumed) range of each model parameter.

At the sourced nominals (config/params.yaml, config/track.yaml) and at the low and high end of each
parameter's range, one at a time: the support-mode frequency (wheelset modal analysis at 14 t), the
Cramér-Rao bound of k_B0 for the 4-wheel rail-coupled design (N = 50, 60-110 km/h, payload 5.5-22.5 t,
40 dB, roughness levels free, debiased likelihood, expected Fisher information), and the detection limit
for a decrease between two periods, MDC = (1.645 + 1.282) sqrt(2) CRB (no model-form term, uncalibrated).
The data are generated and fitted with the same (swept) model: this is a bound sweep, not a misspecification
study. Rows: results/p4/sweep_runs.jsonl (resumable, 110-minute budget per process); --summarise ->
results/p4/sweep.json.
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

from experiments.p1_fe_direct import ISO3095_FIG2_DB, K_SUB, TRUTH, WIM  # noqa: E402
from experiments.p2_relative_change import gen  # noqa: E402
from src.analysis.bound_scan import Scenario, ScenarioModel, support_mode  # noqa: E402
from src.analysis.multiwheel import MultiWheelFamily  # noqa: E402
from src.inverse.multipass import MultiPassWhittle  # noqa: E402
from src.inverse.whittle import Roughness  # noqa: E402
from src.reference.params import Params, load_raw  # noqa: E402
from src.utils.results import RESULTS_DIR, save_result  # noqa: E402

OUT = RESULTS_DIR / "p4"
Z = 1.6448536269514722 + 1.2815515655446004

# (name, kind, path or key, low, high, source label)
SWEEP = [
    ("kB0", "truth", "kB0", 0.5e9, 3.0e9, "assumed, swept"),
    ("axlebox_mass", "param", ("axlebox", "mass"), 100.0, 158.4, "sourced range"),
    ("kp", "param", ("primary", "kp"), 0.98e6, 2.6e6, "sourced range"),
    ("cp", "param", ("primary", "cp"), 5.0e3, 5.0e5, "assumed, swept (heavy-haul range)"),
    ("wheel_diametral_inertia", "param", ("wheel", "diametral_inertia"), 10.0, 30.0, "assumed, swept"),
    ("axle_damping_zeta", "param", ("axle", "damping_zeta"), 0.001, 0.01, "sourced range"),
    ("r0", "param", ("wheel", "r0"), 0.42, 0.46, "sourced range"),
    ("cB", "truth", "cB", 3.0e3, 1.2e4, "assumed, swept (factor 2 about the sourced 6740 N s/m)"),
    ("kf", "track", "kf", 123.0e6, 1333.0e6, "sourced range (derived)"),
    ("eta_f", "track", "eta_f", 0.10, 0.25, "sourced range"),
    ("kH0", "contact", "kH0", 1.4e9, 2.3e9, "sourced range"),
]


def build(override=None):
    raw = load_raw()
    if override:
        node = raw
        for k in override[0][:-1]:
            node = node[k]
        node[override[0][-1]]["value"] = override[1]
    p = Params(raw)
    sm = ScenarioModel(p, Scenario(name="a_iv", kB0=1e9, cB=5e3, contact="hertz_rail", band_hz=700, fs=2000,
                                   forcing_spec={}, targets=["log_kB0"], kH0=1.4e9))
    thb = {"kB0": 1e9, "cB": 5e3, "k_r": 1e8, "r0": p.r0}
    return p, sm, thb


def evaluate(name, kind, key, value):
    from experiments.p2_multiwheel import models
    p, sm, thb = build((key, value) if kind == "param" else None)
    kw = {key: value} if kind == "track" else {}
    mws, track = models(sm, **kw)
    mw = mws["4"]
    if kind == "contact":
        mw.kH0 = value
    tv = dict(TRUTH)
    if kind == "truth":
        tv[key] = value
    th_true = dict(thb, **tv)
    bands = np.array(sorted(ISO3095_FIG2_DB))
    rough = Roughness(bands, np.array([ISO3095_FIG2_DB[b] for b in bands]), K=K_SUB)
    P, Wm, Ws, g = gen(sm, th_true, rough, mw, (51, 0), g_sd=0.0)
    fam = MultiWheelFamily(mw, thb)
    est = MultiPassWhittle(P, Ws, WIM, rough, fam, debias=True)
    crb = est.expected_fisher(np.log([tv["kB0"], tv["cB"]]), np.zeros(est.S), np.log(Ws))["crb_log"]
    ms = support_mode(sm.modes(dict(th_true, W=14.0), 16))
    return {"crb_kB0_pct": 100 * crb[0], "crb_cB_pct": 100 * crb[1], "mdc_pct": 100 * Z * math.sqrt(2) * crb[0],
            "support_mode_hz": ms["f_hz"], "support_mode_zeta": ms["zeta"]}


def run(names):
    OUT.mkdir(parents=True, exist_ok=True)
    fp = OUT / "sweep_runs.jsonl"
    done = {(r["param"], r["point"]) for r in (json.loads(l) for l in fp.read_text().splitlines())} if fp.exists() else set()
    t0, tmax = time.perf_counter(), 10 * 60
    jobs = [("nominal", "none", None, None, "nominal")] if ("nominal", "nominal") not in done else []
    for nm, kind, key, lo, hi, src in SWEEP:
        if names and nm not in names:
            continue
        for pt, v in (("low", lo), ("high", hi)):
            if (nm, pt) not in done:
                jobs.append((nm, kind, key, v, pt))
    for nm, kind, key, v, pt in jobs:
        if time.perf_counter() - t0 + tmax > 110 * 60:
            print("deadline", flush=True)
            break
        t1 = time.perf_counter()
        r = evaluate(nm, kind, key, v) if kind != "none" else evaluate("nominal", "none", None, None)
        row = {"param": nm, "point": pt, "value": v, **r, "wall_s": time.perf_counter() - t1}
        with fp.open("a") as fh:
            fh.write(json.dumps(row) + "\n")
        print(row, flush=True)
        tmax = max(tmax, 1.3 * row["wall_s"])


def summarise():
    rows = [json.loads(l) for l in (OUT / "sweep_runs.jsonl").read_text().splitlines() if l.strip()]
    nom = next(r for r in rows if r["param"] == "nominal")
    table = []
    for nm, kind, key, lo, hi, src in SWEEP:
        R = {r["point"]: r for r in rows if r["param"] == nm}
        if "low" in R and "high" in R:
            table.append({"param": nm, "low": lo, "high": hi, "source": src,
                          **{f"{q}_{pt}": R[pt][q] for pt in ("low", "high") for q in ("crb_kB0_pct", "mdc_pct", "support_mode_hz")}})
    save_result("p4/sweep", {"nominal": nom, "table": table}, cfg={"design": "4-wheel, N = 50, 60-110 km/h, 40 dB, g_sd 0",
                                                                   "mdc": "(1.645+1.282) sqrt(2) CRB, uncalibrated"}, seed=51)
    print(json.dumps({"nominal": nom, "table": table}, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--summarise", action="store_true")
    ap.add_argument("--names", nargs="*", default=None)
    a = ap.parse_args()
    if a.run:
        run(a.names)
    if a.summarise:
        summarise()
