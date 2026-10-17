"""Diagnostic: can the S2-PINN architecture (paper defaults) represent the diffusion solution?

Supervised fit of the same model to the exact manufactured solution (MSE on u, no physics),
same optimiser and batch size as the Nc=4096 run, single-threaded. If supervised error drops
far below the physics-trained plateau, the plateau is an optimisation/loss-balance effect,
not a representation limit. Writes results/p0/repro_representability.json.
"""

from __future__ import annotations

import os

os.environ["OMP_NUM_THREADS"] = "1"

import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

import torch  # noqa: E402

torch.set_num_threads(1)
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "third_party" / "s2pinn" / "src"))

from spinn import train as s2  # noqa: E402

from experiments.p0_reproduce_s2pinn import build_cfg  # noqa: E402
from src.utils.results import save_result  # noqa: E402


def main(steps: int = 1500) -> None:
    cfg = build_cfg(42, None, None)
    R = cfg["model"]["stochastic"]["R"]
    cfg["eval"]["z_eval"] = [{"name": "Z0", "values": [0.0] * R}]
    dev, dt = torch.device("cpu"), torch.float32
    s2.set_seed(42)
    model = s2.build_model(cfg, dev)
    pde = s2.build_pde(cfg)
    opt = torch.optim.Adam(model.parameters(), lr=cfg["training"]["lr"])
    hist = []
    t0 = time.perf_counter()
    for step in range(steps):
        b = pde.sample_collocation(4096, dev, dt)
        t, x, y, Z = b["t"].squeeze(-1), b["x"].squeeze(-1), b["y"].squeeze(-1), b["Z"]
        loss = ((model(t, x, y, Z) - pde.exact_solution(t, x, y, Z)) ** 2).mean()
        opt.zero_grad()
        loss.backward()
        opt.step()
        model.cp.normalize_factors()
        if (step + 1) % 500 == 0:
            m = s2.evaluate(model, pde, cfg["eval"], dev, dt)
            hist.append({"step": step + 1, "mse": float(loss), "mean_rel_l2": m["uq/mean_rel_l2"], "var_rel_l2": m["uq/var_rel_l2"]})
            print(hist[-1], flush=True)
    save_result("p0/repro_representability", {"history": hist, "note": "supervised fit to exact u; same model/optimiser"},
                cfg=cfg, seed=42, wall_seconds=time.perf_counter() - t0)


if __name__ == "__main__":
    main()
