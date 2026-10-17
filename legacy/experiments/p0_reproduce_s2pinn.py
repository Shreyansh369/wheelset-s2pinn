"""P0.1: reproduce the S2-PINN stochastic-diffusion result (paper Table 1).

Runs the authors' released trainer (third_party/s2pinn, pinned commit) with the
paper's stated defaults (Appendix E): R=5, p=3, M=256, Mt=17, q=16, 20k Adam
steps, batches of 32,768, all loss weights 1, lambda_fac=0.1. The released
``configs/base.yaml`` is the diffusion config but ships with R=3, so R is
overridden to 5 (which also sets kl.n_terms=5, as the released CLI does).

The headline metric is ``uq/mean_rel_l2`` from the *final* evaluation, which is
the paper's Table 1 metric (MC over 1024 Z at 2048 probes). G0 needs it within
2x of the paper's 3.71e-3, i.e. <= 7.42e-3.

Usage:
    python experiments/p0_reproduce_s2pinn.py --seed 42            # full run
    python experiments/p0_reproduce_s2pinn.py --seed 42 --steps 20 # smoke test
"""

from __future__ import annotations

import argparse
import copy
import sys
import tempfile
import time
from pathlib import Path

import torch
import yaml

REPO = Path(__file__).resolve().parents[1]
S2PINN_SRC = REPO / "third_party" / "s2pinn" / "src"
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(S2PINN_SRC))

from spinn import train as s2_train  # noqa: E402

from src.utils.results import save_result  # noqa: E402

PAPER_DIFFUSION_MEAN_REL_L2 = 3.71e-3  # Table 1, S2-PINN (proj), diffusion
PAPER_DIFFUSION_VAR_REL_L2 = 4.40e-3  # Table 2
PINNED_COMMIT = "1cd6fa2973ef012900683b8ef3bb94f23f1ade86"


def build_cfg(seed: int, steps: int | None, threads: int | None) -> dict:
    # base.yaml contains a non-UTF-8 byte in a comment (an em dash saved in a
    # legacy code page), so the released load_config fails on UTF-8 locales.
    # Decode with replacement; only comment text is affected.
    raw = (S2PINN_SRC / "configs" / "base.yaml").read_bytes().decode("utf-8", errors="replace")
    cfg = yaml.safe_load(raw)
    cfg["model"]["stochastic"]["R"] = 5
    cfg["pde"]["kl"]["n_terms"] = 5
    cfg["model"]["stochastic"]["p"] = 3
    cfg["seed"] = seed
    cfg["logging"]["use_wandb"] = False
    cfg["eval"]["uq"]["enabled"] = True
    if steps is not None:
        cfg["training"]["steps"] = steps
    return cfg


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--steps", type=int, default=None, help="override 20k (smoke tests only)")
    ap.add_argument("--threads", type=int, default=None)
    ap.add_argument("--tag", type=str, default="")
    args = ap.parse_args()

    if args.threads:
        torch.set_num_threads(args.threads)
    cfg = build_cfg(args.seed, args.steps, args.threads)
    full = cfg["training"]["steps"] == 20000

    with tempfile.TemporaryDirectory() as tmp:
        run_cfg = copy.deepcopy(cfg)
        run_cfg["logging"]["log_dir"] = tmp
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
        t0 = time.perf_counter()
        s2_train.train(run_cfg)
        wall = time.perf_counter() - t0
        ckpt = next(Path(tmp, "ckpt").glob("*.pt"))
        state = torch.load(ckpt, map_location="cpu", weights_only=False)

    final = state["final_metrics"]
    mean_err = final["uq/mean_rel_l2"]
    payload = {
        "full_paper_budget": full,
        "device": "cuda:" + torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu",
        "s2pinn_commit": PINNED_COMMIT,
        "final_metrics": final,
        "best_metrics_during_training": state["best_metrics"],
        "paper_mean_rel_l2": PAPER_DIFFUSION_MEAN_REL_L2,
        "paper_var_rel_l2": PAPER_DIFFUSION_VAR_REL_L2,
        "g0_threshold_mean_rel_l2": 2 * PAPER_DIFFUSION_MEAN_REL_L2,
        "g0_pass": bool(full and mean_err <= 2 * PAPER_DIFFUSION_MEAN_REL_L2),
        "ratio_to_paper": mean_err / PAPER_DIFFUSION_MEAN_REL_L2,
    }
    name = f"p0/s2pinn_repro_seed{args.seed}{args.tag}"
    if not full:
        name += f"_smoke{cfg['training']['steps']}"
    path = save_result(name, payload, cfg=cfg, seed=args.seed, wall_seconds=wall)
    print(f"mean_rel_l2={mean_err:.4e} (paper {PAPER_DIFFUSION_MEAN_REL_L2:.2e}); wrote {path}")


if __name__ == "__main__":
    main()
