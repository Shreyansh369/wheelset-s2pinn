"""Phase 1 MC reference: 10,000 samples of L1-lin (seed 42).

Writes results/p1/mc_ref_seed42.npz (raw arrays, gitignored, regenerable) and
results/p1/mc_ref_seed42.json (per-order moments of left-axlebox acceleration and
axle deflection, Monte Carlo standard errors, and FE cost per sample).
Single-threaded.
"""

from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "1"

import argparse  # noqa: E402
import math  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.reference.mc import run_mc  # noqa: E402
from src.reference.params import load_params  # noqa: E402
from src.utils.results import RESULTS_DIR, Timer, save_result  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10_000)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    p = load_params()
    with Timer() as tm:
        d = run_mc(p, args.n, args.seed)
    out = RESULTS_DIR / "p1" / f"mc_ref_seed{args.seed}.npz"
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out, **{k: v for k, v in d.items() if isinstance(v, np.ndarray)},
                        var_names=np.array(d["var_names"]))
    acc = d["acc"]  # [n, n_w] complex amplitude of left-axlebox acceleration per order
    p2 = np.abs(acc) ** 2
    Q = d["w_unit"] * (acc / d["acc_unit"])[:, :, None]  # deflection amplitudes per order and node
    payload = {
        "n": args.n, "freq_hz": (d["omegas"] / (2 * math.pi)).tolist(),
        "axlebox_accel": {
            "mean_re": acc.real.mean(0).tolist(), "mean_im": acc.imag.mean(0).tolist(),
            "var": p2.mean(0).tolist(),  # E|c|^2 (mean is zero by symmetry of zeta_2)
            "var_mc_std_err": (p2.std(0) / math.sqrt(args.n)).tolist(),
            "rms_m_s2": np.sqrt(0.5 * p2.mean(0)).tolist(),
        },
        "axle_deflection_var_per_order_max_over_nodes": np.max(np.mean(np.abs(Q) ** 2, axis=0), axis=1).tolist(),
        "fe_seconds_per_sample_7_freqs": d["seconds_per_sample"],
        "npz": str(out.relative_to(RESULTS_DIR.parent)),
    }
    save_result(f"p1/mc_ref_seed{args.seed}", payload, cfg={"n": args.n, "seed": args.seed, "threads": 1},
                seed=args.seed, wall_seconds=tm.seconds)
    print({k: payload[k] for k in ("freq_hz", "fe_seconds_per_sample_7_freqs")})
    print("rms accel per order", np.round(payload["axlebox_accel"]["rms_m_s2"], 5))


if __name__ == "__main__":
    main()
