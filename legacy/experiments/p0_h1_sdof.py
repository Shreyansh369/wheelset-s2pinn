"""P0.3: H1 on an SDOF oscillator.

Required gPC degree for a 1% relative variance error of the receptance, as a
function of Pi = s / zeta (s = natural-frequency CoV), for a uniform stiffness
(Legendre basis, as for theta and W in the paper) and a log-normal stiffness
(Hermite basis).

Primary grid (as specified): zeta in {0.5, 1, 2, 5}%, stiffness CoV in
{2, 5, 10, 20}%. Supplement (labelled separately): 12 log-spaced CoVs in
[1%, 30%] at the same dampings, to pin down the slope.

Writes results/p0/h1_sdof.json and two figures.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.analysis.sdof import fit_loglog_slope, run_case  # noqa: E402
from src.utils.results import RESULTS_DIR, Timer, save_result  # noqa: E402

ZETAS = [0.005, 0.01, 0.02, 0.05]
COVS_PRIMARY = [0.02, 0.05, 0.10, 0.20]
COVS_SUPPLEMENT = [float(c) for c in np.geomspace(0.01, 0.30, 12)]
P_MAX = {"legendre": 1000, "hermite": 3000}
TOL = 0.01
FIXED_P = [2, 4, 6, 8]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-supplement", action="store_true")
    ap.add_argument("--figures-only", action="store_true", help="redraw figures from results/p0/h1_sdof.json")
    args = ap.parse_args()
    if args.figures_only:
        from src.utils.results import load_result

        rec = load_result("p0/h1_sdof")["payload"]
        make_figures(rec["rows"], rec["fits_log_p_vs_log_Pi"])
        return

    cfg = {"zetas": ZETAS, "covs_primary": COVS_PRIMARY, "covs_supplement": [] if args.no_supplement else COVS_SUPPLEMENT,
           "p_max": P_MAX, "tol_rel_variance_error": TOL, "band_over_mean_wn": [0.5, 1.5], "n_band": 801,
           "damper": "deterministic c = 2*zeta (zeta is the ratio at mean stiffness)",
           "quadrature": "composite Gauss-Legendre, 2000 panels x 10 nodes; Hermite cut |xi|<=10"}
    rows = []
    with Timer() as tm:
        for family in ("legendre", "hermite"):
            for grid, covs in (("primary", COVS_PRIMARY), ("supplement", cfg["covs_supplement"])):
                for zeta in ZETAS:
                    for cov in covs:
                        r = run_case(family, zeta, cov, P_MAX[family], tol=TOL)
                        rows.append({
                            "family": family, "grid": grid, "zeta": zeta, "cov_k": cov, "s": r.s, "Pi": r.Pi, "Pi2": r.Pi**2,
                            "p_req_at_mean": r.p_req_at_mean, "p_req_band": r.p_req_band,
                            "worst_band_omega": r.worst_band_omega, "quad_check_rel": r.quad_check_rel,
                            "var_err_at_fixed_p": {str(p): float(r.var_err_at_mean[p]) for p in FIXED_P},
                        })
                        print(f"{family:8s} {grid:10s} zeta={zeta:.3f} cov={cov:.3f} Pi={r.Pi:7.3f} "
                              f"p_mean={r.p_req_at_mean} p_band={r.p_req_band}")

    fits = {}
    for family in ("legendre", "hermite"):
        for which in ("p_req_at_mean", "p_req_band"):
            for subset, keep in (("all_uncensored_p>=1", lambda r: True), ("p>=3", lambda r: r[which] >= 3)):
                sel = [r for r in rows if r["family"] == family and r[which] is not None and r[which] >= 1 and keep(r)]
                if len(sel) < 3:
                    continue
                f = fit_loglog_slope(np.array([r["Pi"] for r in sel]), np.array([r[which] for r in sel], float))
                f["slope_vs_Pi2"] = f["slope"] / 2
                f["slope_se_vs_Pi2"] = f["slope_se"] / 2
                fits[f"{family}/{which}/{subset}"] = f
        cens = [r for r in rows if r["family"] == family and r["p_req_at_mean"] is None]
        fits[f"{family}/n_censored_at_mean"] = len(cens)

    payload = {"rows": rows, "fits_log_p_vs_log_Pi": fits,
               "note": "slope 1 vs log Pi means p ~ Pi (= (Pi^2)^0.5); slope 2 means p ~ Pi^2"}
    save_result("p0/h1_sdof", payload, cfg=cfg, wall_seconds=tm.seconds)
    make_figures(rows, fits)
    for k, v in fits.items():
        print(k, v)


def make_figures(rows: list[dict], fits: dict) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colors = {"legendre": "#2a78d6", "hermite": "#eb6834"}  # palette slots 1, 2
    label = {"legendre": "uniform k, Legendre", "hermite": "log-normal k, Hermite"}
    ink, muted, grid = "#0b0b0b", "#52514e", "#e4e3df"

    def style(ax):
        ax.grid(True, which="major", color=grid, lw=0.8)
        ax.set_axisbelow(True)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color(muted)
        ax.tick_params(colors=muted)

    # Figure 1: required degree vs Pi^2
    fig, ax = plt.subplots(figsize=(6.4, 4.6), dpi=150)
    for fam in ("legendre", "hermite"):
        for grid_name, mk, fill in (("primary", "o", True), ("supplement", "o", False)):
            sel = [r for r in rows if r["family"] == fam and r["grid"] == grid_name and r["p_req_at_mean"]]
            if not sel:
                continue
            x = [r["Pi2"] for r in sel]
            y = [r["p_req_at_mean"] for r in sel]
            ax.scatter(x, y, s=36 if fill else 22, marker=mk, facecolors=colors[fam] if fill else "none",
                       edgecolors=colors[fam], linewidths=1.2, zorder=3,
                       label=f"{label[fam]} ({grid_name})")
        f = fits.get(f"{fam}/p_req_at_mean/p>=3")
        if f:
            xs = np.geomspace(min(r["Pi2"] for r in rows if r["family"] == fam and r["p_req_at_mean"] and r["p_req_at_mean"] >= 3),
                              max(r["Pi2"] for r in rows if r["family"] == fam and r["p_req_at_mean"]), 50)
            ax.plot(xs, np.exp(f["intercept"]) * xs ** f["slope_vs_Pi2"], color=colors[fam], lw=2, ls="--", zorder=2)
            txt = f"{fam.capitalize()} fit (p≥3): p ∝ (Π²)^{f['slope_vs_Pi2']:.3f}±{f['slope_se_vs_Pi2']:.3f}"
            if fam == "hermite":
                ax.annotate(txt, (xs[-1], np.exp(f["intercept"]) * xs[-1] ** f["slope_vs_Pi2"]),
                            textcoords="offset points", xytext=(-14, 10), ha="right", color=ink, fontsize=9)
            else:
                ax.text(0.98, 0.06, txt, transform=ax.transAxes, ha="right", color=ink, fontsize=9)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(r"$\Pi^2 = (s/\zeta)^2$", color=ink)
    ax.set_ylabel("gPC degree for 1% variance error", color=ink)
    ax.set_title("SDOF at the mean natural frequency", color=ink, fontsize=11, loc="left")
    style(ax)
    ax.legend(frameon=False, fontsize=8, labelcolor=muted)
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "p0" / "h1_sdof_preq.png")
    plt.close(fig)

    # Figure 2: variance error at fixed degree vs Pi^2 (one panel per family, shared y)
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.6), dpi=150, sharey=True)
    shades = {2: 0.35, 4: 0.55, 6: 0.75, 8: 1.0}
    for ax, fam in zip(axes, ("legendre", "hermite")):
        sel = sorted([r for r in rows if r["family"] == fam], key=lambda r: r["Pi2"])
        x = np.array([r["Pi2"] for r in sel])
        for p in FIXED_P:
            y = np.array([max(r["var_err_at_fixed_p"][str(p)], 1e-16) for r in sel])
            ax.plot(x, y, "o", ms=3.5, color=colors[fam], alpha=shades[p], label=f"p = {p}")
        ax.axhline(TOL, color=muted, lw=1, ls=":")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel(r"$\Pi^2$", color=ink)
        ax.set_title(label[fam], color=ink, fontsize=10, loc="left")
        style(ax)
    axes[0].set_ylabel("relative variance error", color=ink)
    axes[1].legend(frameon=False, fontsize=8, labelcolor=muted)
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "p0" / "h1_sdof_fixed_p.png")
    plt.close(fig)


if __name__ == "__main__":
    main()
