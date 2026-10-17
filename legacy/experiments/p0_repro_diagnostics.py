"""Diagnose the S2-PINN reproduction plateau (mean rel. L2 ~0.27). Writes results/p0/repro_diagnostics.json.

1. The exact manufactured solution passed through the released evaluation pipeline (must give ~0).
2. The released PDE residual evaluated on the exact solution (must be ~0).
3. Run config vs the paper's Appendix E defaults.
4. Dissection of the latest Nc=4096 checkpoint: error vs time, best scalar fit of the mean,
   boundary/initial values, learned bases, loss-term scales.
Single-threaded so the training run keeps its cores.
"""

from __future__ import annotations

import os

os.environ["OMP_NUM_THREADS"] = "1"

import math  # noqa: E402
import shutil  # noqa: E402
import sys  # noqa: E402
import tempfile  # noqa: E402
from pathlib import Path  # noqa: E402

import torch  # noqa: E402

torch.set_num_threads(1)
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "third_party" / "s2pinn" / "src"))

from spinn import train as s2  # noqa: E402

from experiments.p0_reproduce_s2pinn import build_cfg  # noqa: E402
from src.model.moments import cp_stochastic_coeffs  # noqa: E402
from src.utils.results import save_result  # noqa: E402

APPENDIX_E = {"lr": 1e-3, "steps": 20000, "M": 256, "Mt": 17, "q": 16, "R": 5, "p": 3, "dist": "gaussian",
              "w_pde": 1.0, "w_proj": 1.0, "w_bc": 1.0, "w_ic": 1.0, "w_orth": 1.0, "w_fac_orth": 0.1,
              "normalize_cp_every": 1, "batch_pde_bc_ic": 32768, "resample_every": 1, "grad_accum": 1}


class ExactModel(torch.nn.Module):
    def __init__(self, pde):
        super().__init__()
        self.pde = pde

    def forward(self, t, x, y, z):
        return self.pde.exact_solution(t, x, y, z)


def config_diff(cfg: dict, colloc: int) -> dict:
    m, t = cfg["model"], cfg["training"]
    run = {"lr": t["lr"], "steps": t["steps"], "M": m["spatial"]["n_atoms"], "Mt": 1 + 2 * m["temporal"]["n_freq"],
           "q": m["cp"]["rank"], "R": m["stochastic"]["R"], "p": m["stochastic"]["p"], "dist": m["stochastic"]["dist"],
           "w_pde": t["w_pde"], "w_proj": t["w_proj"], "w_bc": t["w_bc"], "w_ic": t["w_ic"], "w_orth": t["w_orth"],
           "w_fac_orth": t["w_fac_orth"], "normalize_cp_every": t["normalize_cp_every"],
           "batch_pde_bc_ic": [colloc, t["bc"], t["ic"]], "resample_every": t["resample_every"],
           "grad_accum": t["grad_accum"]}
    out = {}
    for k, v in APPENDIX_E.items():
        r = run[k]
        same = (r == v) if k != "batch_pde_bc_ic" else (r == [v, v, v])
        out[k] = {"paper": v, "run": r, "match": bool(same)}
    out["extra_not_in_paper"] = {"kl_n_terms": cfg["pde"]["kl"]["n_terms"], "kl_sigma": cfg["pde"]["kl"]["sigma"],
                                 "corr_length": cfg["pde"]["kl"]["corr_length"], "use_warp": m["spatial"]["use_warp"],
                                 "init_sigma": m["spatial"]["init_sigma"], "amp": t["amp"],
                                 "lbfgs_steps": t.get("lbfgs_steps", 0)}
    return out


def main() -> None:
    cfg = build_cfg(42, None, None)
    R = cfg["model"]["stochastic"]["R"]
    cfg["eval"]["z_eval"] = [{"name": "Z0", "values": [0.0] * R}]
    dev, dt = torch.device("cpu"), torch.float32
    torch.manual_seed(0)
    pde = s2.build_pde(cfg)
    out: dict = {}

    # 1. exact solution through the released evaluation
    out["exact_through_eval"] = s2.evaluate(ExactModel(pde), pde, cfg["eval"], dev, dt)

    # 2. released residual on the exact solution (float64 autograd)
    n = 4096
    b = pde.sample_collocation(n, dev, torch.float64)
    t, x, y, Z = (b["t"].squeeze(-1), b["x"].squeeze(-1).requires_grad_(True),
                  b["y"].squeeze(-1).requires_grad_(True), b["Z"])
    tt = t.clone().requires_grad_(True)
    u = pde.exact_solution(tt, x, y, Z)
    gx, gy, gt = torch.autograd.grad(u.sum(), (x, y, tt), create_graph=True)
    lap = torch.autograd.grad(gx.sum(), x, retain_graph=True)[0] + torch.autograd.grad(gy.sum(), y)[0]
    r = pde.compute_residual(t, x, y, Z, {"u": u, "u_t": gt, "laplacian_u": lap})
    s = pde.source_term(t, x, y, Z)
    out["exact_residual"] = {"max_abs": float(r.abs().max()), "rms": float(r.pow(2).mean().sqrt()),
                             "rms_source": float(s.pow(2).mean().sqrt()),
                             "operator": "u_t - k*laplacian(u) - s (non-divergence; paper text writes div(k grad u))"}

    # 3. config diff
    out["config_vs_appendix_E"] = config_diff(cfg, 4096)

    # 4. checkpoint dissection
    ck = REPO / "results" / "p0" / "ckpt" / "s2pinn_repro_seed42_nc4096_steps20000.pt"
    with tempfile.TemporaryDirectory() as tmp:
        cp = Path(tmp) / "c.pt"
        shutil.copy(ck, cp)
        st = torch.load(cp, map_location="cpu", weights_only=False)
    torch.manual_seed(0)
    model = s2.build_model(cfg, dev)
    model.load_state_dict(st["model"])
    model.eval()
    d = {"step": st["step"]}
    with torch.no_grad():
        g = torch.linspace(-1, 1, 81)
        X, Y = torch.meshgrid(g, g, indexing="ij")
        xs, ys = X.reshape(-1), Y.reshape(-1)
        per_t = {}
        for tv in (0.0, 0.25, 0.5, 0.75, 1.0):
            tv_ = torch.full_like(xs, tv)
            Fs = model.spatial(xs, ys)
            Ft, _ = model.temporal(tv_)
            c = cp_stochastic_coeffs(Fs @ model.cp.A, Ft @ model.cp.B, model.cp.D, model.cp.w)  # [P, G]
            mean_pred = c[:, 0]  # E_Z[u]: Psi_0 = 1 and every other Hermite mode has zero mean
            mean_ref = torch.sin(math.pi * xs) * torch.sin(math.pi * ys) * math.exp(-tv)
            alpha = float((mean_pred @ mean_ref) / (mean_ref @ mean_ref))
            rel = float((mean_pred - mean_ref).norm() / mean_ref.norm())
            rel_scaled = float((mean_pred - alpha * mean_ref).norm() / mean_ref.norm())
            edge = (xs.abs() == 1) | (ys.abs() == 1)
            per_t[str(tv)] = {"mean_rel_l2": rel, "best_scale_alpha": alpha, "rel_l2_after_scaling": rel_scaled,
                              "boundary_rms_of_mean": float(mean_pred[edge].pow(2).mean().sqrt()),
                              "interior_peak_pred": float(mean_pred.max()), "interior_peak_ref": float(mean_ref.max())}
        d["mean_field_by_time"] = per_t
        d["time_freqs"] = torch.exp(model.temporal.log_omega).tolist()
        sig = torch.exp(model.spatial.log_sigma)
        d["atom_sigma"] = {"min": float(sig.min()), "median": float(sig.median()), "max": float(sig.max())}
        d["atom_centres_outside_domain"] = int((model.spatial.centers.abs() > 1).any(1).sum())
        d["cp_w"] = model.cp.w.tolist()
    out["checkpoint"] = d
    save_result("p0/repro_diagnostics", out, cfg=cfg)
    import json

    print(json.dumps({k: v for k, v in out.items() if k != "config_vs_appendix_E"}, indent=1, default=float)[:5000])
    print({k: v for k, v in out["config_vs_appendix_E"].items() if k == "extra_not_in_paper" or not v["match"]})


if __name__ == "__main__":
    main()
