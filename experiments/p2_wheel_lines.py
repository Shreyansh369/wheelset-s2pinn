"""Task (b): wheel roughness at rotation orders. Notch the order bins vs model them as tachometer lines.

Wheel roughness: periodic profile on the instrumented wheel(s) with the ISO 3095 limit shape plus
delta = 0 or +10 dB (an assumption scanned, not a sourced wheel-roughness level), one draw per
dataset, identical on every pass. Records are angle-synchronous (20 revolutions after tachometer
resampling), so order n falls exactly on bin 20 n.
Estimators: "ignore" (lines treated as rail roughness bins), "notch" (order bins removed from the
likelihood, i.e. option i), "tacho" (order bins carry a shared complex line w_n per order, option ii).
--bound: kB0/cB CRB for notch and tacho (and the no-wheel-roughness reference), fixed 100 and
60-110 km/h. --mc: 10 datasets per delta at 60-110 km/h, N = 50, SNR 40 dB, all three estimators.
"""

from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "1"

import argparse  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.p2_common import TRUTH, WIM, make_dataset, phi_start, phi_true, setup, summarise  # noqa: E402
from src.inverse.multipass import N_REVS, MultiPassWhittle, SingleWheelsetFamily  # noqa: E402
from src.inverse.variants import WheelLineWhittle  # noqa: E402
from src.utils.results import RESULTS_DIR, Timer, save_result  # noqa: E402

RUN_DIR = RESULTS_DIR / "p2" / "wheel_lines_runs"
SPEEDS = {"fixed_100": (100.0, 100.0), "uniform_60_110": (60.0, 110.0)}


def estimators(ds, rough, fam):
    P = ds["passes"]
    return {"ignore": MultiPassWhittle([dict(q) for q in P], ds["Wm"], WIM, rough, fam),
            "notch": MultiPassWhittle([dict(q) for q in P], ds["Wm"], WIM, rough, fam, mask=lambda p: p["k"] % N_REVS != 0),
            "tacho": WheelLineWhittle([dict(q) for q in P], ds["Wm"], WIM, rough, fam)}


def true_w(est, ds):
    return ds["wheel"]["w"][est.orders - 1]


def bound():
    sm, thb, rough, _ = setup()
    fam = SingleWheelsetFamily(sm, thb)
    rows = []
    with Timer() as tm:
        for sname, spd in SPEEDS.items():
            ref = make_dataset(sm, thb, rough, (77, 0), speeds=spd)
            c0 = MultiPassWhittle(ref["passes"], ref["Ws"], WIM, rough, fam).expected_fisher(phi_true(), np.log(ref["g"]), np.log(ref["Ws"]))
            rows.append({"speeds": sname, "delta_db": None, "method": "no_wheel_roughness", "crb_kB0": c0["crb_log"][0], "crb_cB": c0["crb_log"][1]})
            for delta in (0.0, 10.0):
                ds = make_dataset(sm, thb, rough, (77, 0), speeds=spd, wheel_delta_db=delta)
                E = estimators(ds, rough, fam)
                cn = E["notch"].expected_fisher(phi_true(), np.log(ds["g"]), np.log(ds["Ws"]))
                ct = E["tacho"].expected_fisher(phi_true(), np.log(ds["g"]), np.log(ds["Ws"]), w_true=true_w(E["tacho"], ds))
                rows += [{"speeds": sname, "delta_db": delta, "method": "notch", "crb_kB0": cn["crb_log"][0], "crb_cB": cn["crb_log"][1]},
                         {"speeds": sname, "delta_db": delta, "method": "tacho", "crb_kB0": ct["crb_log"][0], "crb_cB": ct["crb_log"][1],
                          "n_orders": int(E["tacho"].L)}]
            for r in rows[-5:]:
                print(r, flush=True)
    save_result("p2/wheel_lines_bound", {"rows": rows}, cfg={"N": 50, "snr_db": 40, "wim_sigma": WIM,
                "wheel_roughness": "ISO 3095 limit shape + delta (assumption)", "record": "angle-synchronous, 20 revolutions"},
                seed=77, wall_seconds=tm.seconds)


def mc(n_data, deltas, seed_base=20261012):
    sm, thb, rough, _ = setup()
    fam = SingleWheelsetFamily(sm, thb)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    for delta in deltas:
        fp = RUN_DIR / f"delta{int(delta)}_uniform_60_110.jsonl"
        done = {tuple(json.loads(l)["seed_key"]) for l in fp.read_text().splitlines()} if fp.exists() else set()
        for j in range(n_data):
            key = (seed_base, int(delta), j)
            if key in done:
                continue
            ds = make_dataset(sm, thb, rough, key, wheel_delta_db=delta)
            row = {"delta_db": delta, "seed_key": list(key)}
            for tag, est in estimators(ds, rough, fam).items():
                r = est.fit(phi_start())
                kw = {"w_true": true_w(est, ds)} if tag == "tacho" else {}
                crb = est.expected_fisher(phi_true(), np.log(ds["g"]), np.log(ds["Ws"]), **kw)
                row[tag] = {"err_log": [r["phi"][0] - math.log(TRUTH["kB0"]), r["phi"][1] - math.log(TRUTH["cB"])],
                            "se_log": r["se_log"], "crb_log": crb["crb_log"], "converged": r["converged"],
                            "wall_fit_s": r["wall_fit_s"]}
            with fp.open("a") as fh:
                fh.write(json.dumps(row) + "\n")
            print(f"delta={delta} j={j} " + " ".join(f"{t}={row[t]['err_log'][0]:+.4f}/{row[t]['se_log'][0]:.4f}"
                                                    for t in ("ignore", "notch", "tacho")), flush=True)


def aggregate():
    cells = []
    for fp in sorted(RUN_DIR.glob("*.jsonl")):
        rows = [json.loads(l) for l in fp.read_text().splitlines() if l.strip()]
        cell = {"file": fp.name, "delta_db": rows[0]["delta_db"]}
        for tag in ("ignore", "notch", "tacho"):
            cell[tag] = summarise([r[tag]["err_log"][0] for r in rows], [r[tag]["se_log"][0] for r in rows],
                                  [r[tag]["crb_log"][0] for r in rows])
            cell[tag]["all_converged"] = all(r[tag]["converged"] for r in rows)
        cells.append(cell)
        print(json.dumps(cell), flush=True)
    save_result("p2/wheel_lines_mc", {"cells": cells}, cfg={"N": 50, "speeds_kmh": [60, 110], "snr_db": 40, "truth": TRUTH},
                seed=20261012)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--bound", action="store_true")
    ap.add_argument("--mc", action="store_true")
    ap.add_argument("--aggregate", action="store_true")
    ap.add_argument("--n-data", type=int, default=10)
    ap.add_argument("--deltas", type=float, nargs="+", default=[0.0, 10.0])
    a = ap.parse_args()
    if a.bound:
        bound()
    if a.mc:
        mc(a.n_data, a.deltas)
    if a.aggregate:
        aggregate()
