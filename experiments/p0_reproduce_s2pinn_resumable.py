"""P0.1 on CPU: the S2-PINN diffusion reproduction with checkpoint/resume.

The released ``spinn.train.train`` writes nothing until the end, and a full
20k-step run takes ~23 h on this container's CPU (results/p0/s2pinn_cpu_timing.json).
This runner replays the *same* Adam loop as train() line for line, using the
authors' own functions (build_model, build_pde, sample_batch,
compute_pde_residual, compute_gpc_projection_loss, compute_bc_loss,
compute_ic_loss, model.regularization, cp.normalize_factors, evaluate) in the
same order, so global-RNG consumption matches an uninterrupted train() call:
seed -> model init -> per-step batches -> evaluate() every 500 steps -> final
evaluate(). The only addition is a checkpoint (model, optimizer, RNG state,
best metrics, step, accumulated wall time) right after each 500-step evaluation.
No L-BFGS phase (the released default lbfgs_steps is 0) and no AMP (default "none").

Usage:
    python experiments/p0_reproduce_s2pinn_resumable.py --seed 42          # starts or resumes
    python experiments/p0_reproduce_s2pinn_resumable.py --seed 42 --steps 1000 --tag _test
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import torch

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "third_party" / "s2pinn" / "src"))

from spinn import train as s2  # noqa: E402

from experiments.p0_reproduce_s2pinn import (  # noqa: E402
    PAPER_DIFFUSION_MEAN_REL_L2,
    PAPER_DIFFUSION_VAR_REL_L2,
    PINNED_COMMIT,
    build_cfg,
)
from src.utils.results import save_result  # noqa: E402

CKPT_DIR = REPO / "results" / "p0" / "ckpt"  # *.pt are gitignored


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--steps", type=int, default=None)
    ap.add_argument("--tag", type=str, default="")
    ap.add_argument("--eval-every", type=int, default=None, help="testing only (changes the RNG stream vs the paper run)")
    ap.add_argument("--stop-after-hours", type=float, default=None, help="exit cleanly at the next checkpoint after this")
    args = ap.parse_args()

    cfg = build_cfg(args.seed, args.steps, None)
    tc = cfg["training"]
    steps = tc["steps"]
    full = steps == 20000
    if args.eval_every is not None:
        assert args.tag, "--eval-every is for tests; give a --tag"
        cfg["eval"]["eval_every"] = args.eval_every
    eval_every = cfg["eval"]["eval_every"]
    device, dtype = torch.device("cpu"), torch.float32
    ckpt = CKPT_DIR / f"s2pinn_repro_seed{args.seed}{args.tag}_steps{steps}.pt"
    log_path = REPO / "results" / "p0" / f"s2pinn_repro_seed{args.seed}{args.tag}.log"
    CKPT_DIR.mkdir(parents=True, exist_ok=True)

    # identical construction order to spinn.train.train
    s2.set_seed(cfg["seed"])
    model = s2.build_model(cfg, device)
    pde = s2.build_pde(cfg)
    R = cfg["model"]["stochastic"]["R"]
    cfg["eval"]["z_eval"] = [{"name": "Z0", "values": [0.0] * R}] + [
        {"name": f"Z_e{i + 1}", "values": [1.0 if j == i else 0.0 for j in range(R)]} for i in range(min(R, 2))
    ]  # train() regenerates z_eval this way when R differs from the yaml's 3
    optimizer = torch.optim.Adam(model.parameters(), lr=tc["lr"])
    gpc_basis = model.stochastic
    best: dict[str, float] = {}
    start, wall_prev = 0, 0.0

    if ckpt.exists():
        st = torch.load(ckpt, map_location="cpu", weights_only=False)
        model.load_state_dict(st["model"])
        optimizer.load_state_dict(st["optimizer"])
        torch.set_rng_state(st["rng"])
        best, start, wall_prev = st["best"], st["step"], st["wall"]
        print(f"resumed at step {start} ({wall_prev / 3600:.2f} h so far)", flush=True)

    t_seg = time.perf_counter()
    batches = None
    with log_path.open("a") as log:
        for step in range(start, steps):
            if batches is None or (tc["resample_every"] > 0 and step % tc["resample_every"] == 0):
                batches = s2.sample_batch(pde, tc["colloc"], tc["bc"], tc["ic"], device, dtype)
            optimizer.zero_grad(set_to_none=True)
            residual, _ = s2.compute_pde_residual(model, pde, batches["colloc"])
            loss_pde = (residual**2).mean()
            loss_proj = s2.compute_gpc_projection_loss(residual, batches["colloc"]["Z"], gpc_basis)
            loss_bc = s2.compute_bc_loss(model, pde, batches["bc"])
            loss_ic = s2.compute_ic_loss(model, pde, batches["ic"])
            F_gram = model.spatial(batches["colloc"]["x"].squeeze(-1).detach(), batches["colloc"]["y"].squeeze(-1).detach())
            reg = model.regularization(F_gram, tc["w_orth"], tc["w_fac_orth"])
            loss = tc["w_pde"] * loss_pde + tc["w_proj"] * loss_proj + tc["w_bc"] * loss_bc + tc["w_ic"] * loss_ic + reg
            loss.backward()
            optimizer.step()
            if tc["normalize_cp_every"] > 0 and (step + 1) % tc["normalize_cp_every"] == 0:
                model.cp.normalize_factors()

            if step % 100 == 0:
                log.write(f"{step} total={loss.item():.4e} pde={loss_pde.item():.4e} proj={loss_proj.item():.4e} "
                          f"bc={loss_bc.item():.4e} ic={loss_ic.item():.4e} reg={reg.item():.4e} "
                          f"wall_h={(wall_prev + time.perf_counter() - t_seg) / 3600:.3f}\n")
                log.flush()

            if eval_every > 0 and (step + 1) % eval_every == 0:
                m = s2.evaluate(model, pde, cfg["eval"], device, dtype)
                for k, v in m.items():
                    if k not in best or v < best[k]:
                        best[k] = v
                log.write(f"EVAL {step + 1} mean_rel_l2={m.get('uq/mean_rel_l2', float('nan')):.4e} "
                          f"var_rel_l2={m.get('uq/var_rel_l2', float('nan')):.4e}\n")
                log.flush()
                wall = wall_prev + time.perf_counter() - t_seg
                tmp = ckpt.with_suffix(".tmp")
                torch.save({"model": model.state_dict(), "optimizer": optimizer.state_dict(), "rng": torch.get_rng_state(),
                            "best": best, "step": step + 1, "wall": wall}, tmp)
                tmp.replace(ckpt)
                if args.stop_after_hours is not None and (time.perf_counter() - t_seg) / 3600 >= args.stop_after_hours:
                    print(f"stopping at checkpoint step {step + 1}", flush=True)
                    return

    final = s2.evaluate(model, pde, cfg["eval"], device, dtype)
    wall = wall_prev + time.perf_counter() - t_seg
    mean_err = final["uq/mean_rel_l2"]
    payload = {
        "full_paper_budget": full, "device": "cpu", "runner": "resumable replay of spinn.train.train loop",
        "s2pinn_commit": PINNED_COMMIT, "final_metrics": final, "best_metrics_during_training": best,
        "paper_mean_rel_l2": PAPER_DIFFUSION_MEAN_REL_L2, "paper_var_rel_l2": PAPER_DIFFUSION_VAR_REL_L2,
        "g0_threshold_mean_rel_l2": 2 * PAPER_DIFFUSION_MEAN_REL_L2,
        "g0_pass": bool(full and mean_err <= 2 * PAPER_DIFFUSION_MEAN_REL_L2),
        "ratio_to_paper": mean_err / PAPER_DIFFUSION_MEAN_REL_L2,
        "note": "CPU run: wall time and memory are not comparable with the paper's T4 figures",
    }
    name = f"p0/s2pinn_repro_seed{args.seed}{args.tag}"
    if not full:
        name += f"_steps{steps}"
    path = save_result(name, payload, cfg=cfg, seed=args.seed, wall_seconds=wall)
    print(f"mean_rel_l2={mean_err:.4e} (paper {PAPER_DIFFUSION_MEAN_REL_L2:.2e}); wrote {path}", flush=True)


if __name__ == "__main__":
    main()
