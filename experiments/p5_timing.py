"""Preregistration v2, Step 1: wall time of one unit of each study at the configuration in WHEELSET_CONFIG_DIR.

Each unit is the inner computation of the study, run in this process with the study's own functions; the only
output is one row per unit in results/p5/timing.jsonl (no study row file is written). Units:
  headline   one headline dataset (N = 50, 40 dB) fitted by the frozen estimator, plus its CRB
  a2_2p5     the same at true k_B0 = 2.5 GN/m (start truth / 0.85, as experiments/p3_headline_v2 --kb0-from-config)
  a2_5p0     the same at 5 GN/m
  bounds     one cell of the banded bound (empty band, N = 200, 40 dB): dataset and expected information
  modelform  one pseudo-true fit of the model-form budget (nominal estimator, unsprung mass x 1.1)
  nlcontact  one nonlinear-contact dataset (time-domain Hertz generator) and its fit
The change studies (simultaneous errors, zero change) are timed by running one replicate of experiments/p5_v2.py
with --tag _timing.

    WHEELSET_CONFIG_DIR=config/sensitivity/mass_dusza python3 experiments/p5_timing.py --units headline a2_2p5
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

from experiments.p1_fe_direct import START, TRUTH, WIM  # noqa: E402
from src.utils.results import RESULTS_DIR, _git_commit, config_hash  # noqa: E402

OUT = RESULTS_DIR / "p5" / "timing.jsonl"


def headline(kb0=None):
    from experiments.p2_common import setup
    from experiments.p2_multiwheel import dataset, models
    from src.analysis.multiwheel import MultiWheelFamily
    from src.inverse.multipass import MultiPassWhittle
    tr, st = dict(TRUTH), dict(START)
    if kb0:
        tr["kB0"], st["kB0"] = kb0, kb0 / 0.85
    sm, thb, rough, _ = setup()
    mw = models(sm)[0]["4"]
    fam = MultiWheelFamily(mw, thb)
    import experiments.p2_common as pc
    old = dict(pc.TRUTH)
    pc.TRUTH.update(tr)
    try:
        P, Wm, Ws, g = dataset(sm, thb, rough, mw, (42, 40, 0), N=50, snr=40.0)
    finally:
        pc.TRUTH.clear()
        pc.TRUTH.update(old)
    est = MultiPassWhittle([dict(q) for q in P], Wm, WIM, rough, fam, debias=True, Kb=120, exact_subband=False)
    r = est.fit(np.log([st["kB0"], st["cB"]]))
    crb = est.expected_fisher(np.log([tr["kB0"], tr["cB"]]), np.log(g), np.log(Ws))["crb_log"]
    return {"err_log": r["phi"][0] - math.log(tr["kB0"]), "crb_log": crb[0], "converged": r["converged"], "n_eval": r["n_eval"]}


def bounds():
    import experiments.p4_banded as b
    sm, thb_b, rough, mw, fams = b._base("empty")
    P, Wm, Ws, g = b.pm.dataset(sm, thb_b, rough, mw, (48, 200, 40), N=200, snr=40.0, speeds=b.SPEEDS, g_sd=0.0)
    est = b.MultiPassWhittle(P, Ws, WIM, rough, fams["coest"], debias=True)
    crb = est.expected_fisher(b.phi(b.EST["coest"]), np.zeros(est.S), est.lw_meas.copy())["crb_log"][0]
    return {"crb_pct": 100 * crb}


def modelform():
    import experiments.p2_model_form_mw as mf
    from src.analysis.multiwheel import MultiWheelFamily
    sm, thb, rough, _ = mf.setup()
    mw = mf.models(sm)[0]["4"]
    P, Wm, Ws, g = mf.designs(sm, thb, rough, mw, n=1)[0]
    names = mf.ESTIMATORS["nominal"]
    fam_fit = MultiWheelFamily(mw, dict(thb, **{k: v for k, v in mf.NOM.items() if k not in names}), names=names)
    est = mf.MultiPassWhittle(P, Ws, WIM, rough, fam_fit, debias=True)
    phi0 = np.log([{**mf.START, **mf.NOM}[n] for n in names])
    true_all = dict(thb, **mf.TRUTH, **mf.NOM)
    true_all["unsprung_scale"] = 1.1
    r = est.pseudo_true(MultiWheelFamily(mw, true_all, names=()), {}, np.zeros(est.S), np.log(Ws), phi0)
    return {"bias_pct": (math.exp(r["phi"][0] - math.log(mf.TRUTH["kB0"])) - 1) * 100, "converged": r["converged"]}


def nlcontact():
    import experiments.p4_inverse_crime as ic
    sm, thb, rough, _ = ic.setup()
    mw = ic.models(sm)[0]["4"]
    gen = ic.NonlinearContactGenerator(mw, dict(thb, **TRUTH), pad=ic.PAD[0])
    fam = ic.MultiWheelFamily(mw, thb)
    t0 = time.perf_counter()
    P, Wm, Ws, g, st = ic.dataset(gen, rough, thb["r0"], (60, 0), "hertz")
    t_gen = time.perf_counter() - t0
    r = ic.fit(P, Wm, rough, fam)
    return {"wall_gen_s": t_gen, "err_log": r["phi"][0] - math.log(TRUTH["kB0"]), "converged": r["converged"]}


UNITS = {"headline": headline, "a2_2p5": lambda: headline(2.5e9), "a2_5p0": lambda: headline(5.0e9),
         "bounds": bounds, "modelform": modelform, "nlcontact": nlcontact}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--units", nargs="+", choices=tuple(UNITS), required=True)
    a = ap.parse_args()
    cd = os.environ.get("WHEELSET_CONFIG_DIR", "config")
    for u in a.units:
        t0 = time.perf_counter()
        res = UNITS[u]()
        row = {"unit": u, "config_dir": cd, "config_hash": config_hash(Path(cd)), "wall_s": time.perf_counter() - t0,
               "load_avg_1min": os.getloadavg()[0], "git_commit": _git_commit(), **res,
               "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        OUT.parent.mkdir(parents=True, exist_ok=True)
        with OUT.open("a") as fh:
            fh.write(json.dumps(row) + "\n")
        print(json.dumps(row), flush=True)
