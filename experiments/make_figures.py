"""Paper-1 figures (docs/paper1_outline.md). Reads results/ JSON only (Fig. 1's curves are computed once
from the model and saved to results/p2/fig1_transfer.json with provenance). Writes figures/figN.pdf and .png.

Style: categorical slots 1-4 of the validated reference palette (light mode; adjacent CVD dE >= 9.1;
slots 3-4 are below 3:1 contrast, so every series carries a legend entry or direct label), 1.4 pt lines,
recessive grid, one y-axis per panel. A figure whose source file is missing is skipped with a note.
"""

from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "1"

import json  # noqa: E402
import math  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.utils.results import RESULTS_DIR, save_result  # noqa: E402

OUT = ROOT / "figures"
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]          # categorical slots 1-4 (light)
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
plt.rcParams.update({"font.size": 8.5, "axes.titlesize": 9, "axes.labelsize": 8.5, "legend.fontsize": 7.5,
                     "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.spines.top": False,
                     "axes.spines.right": False, "lines.linewidth": 1.4, "legend.frameon": False,
                     "savefig.dpi": 300, "figure.dpi": 110})


USED: list[str] = []          # result files loaded since the last saved figure
MANIFEST: dict[str, list[str]] = {}


def load(rel):
    USED.append(f"results/{rel}")
    fp = RESULTS_DIR / rel
    return json.loads(fp.read_text())["payload"] if fp.exists() else None


def save(fig, name):
    OUT.mkdir(exist_ok=True)
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(OUT / f"{name}.png", bbox_inches="tight")
    plt.close(fig)
    MANIFEST[name] = sorted(set(USED))
    USED.clear()
    (OUT / "manifest.json").write_text(json.dumps(MANIFEST, indent=1))
    print("wrote", name)


# ----------------------------------------------------------------------------- Fig. 1
def fig1_data():
    d = load("p2/fig1_transfer.json")
    if d is not None:
        return d
    from experiments.p1_fe_direct import TRUTH, setup
    from experiments.p2_multiwheel import models
    sm, thb, rough, _ = setup()
    mws, _ = models(sm)
    f = np.arange(50.0, 700.25, 0.25)
    w = 2 * np.pi * f
    th = dict(thb, **TRUTH, W=14.0)
    out = {"f_hz": f.tolist(), "curves": {}}
    for nw in ("1", "2", "4", "8"):
        G = mws[nw].components(th, w)
        for V in (60.0, 110.0):
            H = (G * np.exp(1j * w[:, None] * mws[nw].d[None, :] / (V / 3.6))).sum(1)
            out["curves"][f"{nw}_{int(V)}"] = (20 * np.log10(np.abs(H))).tolist()
    save_result("p2/fig1_transfer", out, cfg={"truth": TRUTH, "W_t": 14.0, "track": "config nominal (60E1, ballasted freight)",
                                               "layout": "config nominal (Y25/Eanos wagon), subsets of 1/2/4/8 wheels", "quantity": "20 log10 |H|, left-axlebox accel per unit roughness"},
                seed=0)
    return load("p2/fig1_transfer.json")


def fig1():
    d = fig1_data()
    f = np.array(d["f_hz"])
    fig, axs = plt.subplots(2, 3, figsize=(7.0, 4.0), sharex=True, sharey=True)
    for i, V in enumerate((60, 110)):
        for j, nw in enumerate(("2", "4", "8")):
            ax = axs[i, j]
            ax.plot(f, d["curves"][f"{nw}_{V}"], color=C[0], lw=0.7, label=f"{nw} wheels, rail-coupled")
            ax.plot(f, d["curves"][f"1_{V}"], color=C[1], lw=1.4, label="1 wheel (no coupling)")
            ax.set_title(f"{nw} wheels, {V} km/h", color=INK)
            if i == 1:
                ax.set_xlabel("Frequency (Hz)")
        axs[i, 0].set_ylabel("|H| (dB re 1 s$^{-2}$)")
    axs[0, 0].set_xlim(50, 700)
    h, _ = axs[0, 0].get_legend_handles_labels()
    fig.legend(h, ["Multi-wheel, rail-coupled", "Single wheel (no coupling)"], loc="lower center", ncol=2,
               bbox_to_anchor=(0.5, -0.02))
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    save(fig, "fig1_transfer_functions")


# ----------------------------------------------------------------------------- Fig. 2
def fig2():
    d = load("p1/bound_speed_subband.json")
    if d is None:
        return print("skip fig2")
    rows = [r for r in d["rows"] if r["N"] == 50 and r["snr_db"] == 40.0 and r["subband_prior_db"] is None
            and r["payload"].startswith("spread")]
    fig, ax = plt.subplots(figsize=(3.4, 2.6))
    for k, K in enumerate((1, 16, 256)):
        R = sorted([r for r in rows if r["K_per_third_octave"] == K], key=lambda r: r["speed_std_kmh"])
        ax.plot([r["speed_std_kmh"] for r in R], [100 * r["crb_rel_kB0"] for r in R], "o-" if K != 256 else "s--",
                ms=4 if K != 256 else 6, mfc="none" if K == 256 else C[k], color=C[k], zorder=3 - k,
                label=f"K = {K} level{'s' if K > 1 else ''} per 1/3 octave" + (" (on K = 16)" if K == 256 else ""))
    ax.set_ylim(bottom=0)
    ax.set_xlabel("Speed standard deviation across passes (km/h)")
    ax.set_ylabel("CRB of $k_{B0}$ (%)")
    ax.legend()
    save(fig, "fig2_crb_vs_speed_spread")


# ----------------------------------------------------------------------------- Fig. 3
def fig3():
    d = load("p2/debias_check.json")
    if d is None:
        return print("skip fig3")
    f = np.array(d["f_hz"])
    sel = (f > 25) & (f < 140)
    db = lambda x: 10 * np.log10(np.asarray(x)[sel])  # noqa: E731
    fig, (ax, bx) = plt.subplots(2, 1, figsize=(7.0, 3.8), sharex=True, gridspec_kw={"height_ratios": [2, 1]})
    ax.plot(f[sel], db(d["mean_periodogram"]), color=INK2, lw=0.9, label="Mean periodogram (300 records)")
    ax.plot(f[sel], db(d["model_bin_sampled"]), color=C[1], lw=1.0, label="Bin-sampled model |H(f$_k$)|$^2$S")
    ax.plot(f[sel], db(d["model_debiased"]), color=C[0], lw=1.2, ls="--", label="Debiased model (Fejér kernel)")
    s = d["summary_25_140hz"]
    ax.set_title(f"rms log ratio: bin-sampled {s['bin_sampled']['rms_log_ratio']:.2f}, debiased "
                 f"{s['debiased']['rms_log_ratio']:.2f} (sampling noise {s['sampling_noise_rms_log_expected']:.2f})", color=INK)
    ax.set_ylabel("Power (dB)")
    ax.legend(loc="upper right", ncol=3, bbox_to_anchor=(1, 1.0))
    ax.set_ylim(top=ax.get_ylim()[1] + 8)
    for tag, col in (("model_bin_sampled", C[1]), ("model_debiased", C[0])):
        bx.plot(f[sel], db(d["mean_periodogram"]) - db(d[tag]), color=col, lw=1.0)
    bx.axhline(0, color=INK2, lw=0.8)
    bx.set_ylabel("Mean / model (dB)")
    bx.set_xlabel("Frequency (Hz)")
    fig.tight_layout()
    save(fig, "fig3_debiased_periodogram")


# ----------------------------------------------------------------------------- Fig. 4
def fig4():
    d = load("p2/multiwheel_mc.json")
    if d is None:
        return print("skip fig4")
    cells = sorted(d["cells"], key=lambda c: c["wheels"])
    x = np.arange(len(cells))
    fig, ax = plt.subplots(figsize=(3.4, 2.6))
    for k, (tag, lab) in enumerate((("correct", "Rail-coupled model"), ("single_wheelset", "Single-wheelset model (coupling ignored)"))):
        y = [100 * c[tag]["bias_rel_kB0"] for c in cells]
        e = [196 * c[tag]["bias_rel_kB0_se"] for c in cells]
        ax.errorbar(x + (k - 0.5) * 0.18, y, yerr=e, fmt="o", ms=5, color=C[k], label=lab, capsize=2, lw=1.2)
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_xticks(x, [f"{c['wheels']} wheels" for c in cells])
    ax.set_ylabel("Bias of $k_{B0}$ (%), ±95% CI")
    ax.set_ylim(-16, 2)
    ax.legend(loc="center left", bbox_to_anchor=(0.0, 0.42))
    save(fig, "fig4_multiwheel_bias")


# ----------------------------------------------------------------------------- Fig. 5
def fig5():
    d = load("p2/model_form_mw_sensitivity.json")
    if d is None:
        return print("skip fig5")
    names = {"kf": "Foundation stiffness $k_f$", "eta_f": "Foundation loss factor $\\eta_f$", "kH0": "Contact stiffness $k_{H0}$",
             "unsprung_scale": "Unsprung mass", "axle_damp_scale": "Axle damping"}
    fig, axs = plt.subplots(1, 2, figsize=(7.0, 2.4), sharey=True)
    for ax, (est, title) in zip(axs, (("nominal", "Nominal fit"), ("coest", "$k_f$, $k_{H0}$ co-estimated"))):
        T = [t for t in d["table"] if t["estimator"] == est]
        order = list(names)
        for i, p in enumerate(order):
            t = next((t for t in T if t["param"] == p), None)
            if t is None or t["bias_at_minus_1sigma_pct"] is None:
                continue
            lo, hi = t["bias_at_minus_1sigma_pct"], t["bias_at_plus_1sigma_pct"]
            ax.barh(i - 0.17, lo, height=0.32, color=C[0], label="parameter −1σ" if i == 0 else None)
            ax.barh(i + 0.17, hi, height=0.32, color=C[1], label="parameter +1σ" if i == 0 else None)
        b = d["budget"].get(est, {})
        ax.set_title(f"{title}: RSS {b.get('rss_pct', float('nan')):.1f}%", color=INK)
        ax.axvline(0, color=INK2, lw=0.8)
        ax.set_xlabel("Bias of $k_{B0}$ (%)")
        ax.set_yticks(range(len(order)), [f"{names[p]} (σ={math.exp(d['ranges'][p][0]) * 100 - 100:.0f}%)" for p in order])
    axs[0].invert_yaxis()
    h, l = axs[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=2, bbox_to_anchor=(0.6, -0.04))
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    save(fig, "fig5_model_form_tornado")


# ----------------------------------------------------------------------------- Fig. 6
def fig6():
    d = load("p2/relative_change.json")
    ki = load("p2/relative_intervals.json")
    if d is None:
        return print("skip fig6")
    T = d["pseudo_true"]
    cases = sorted({t["case"] for t in T})
    fig, axs = plt.subplots(1, 2, figsize=(7.0, 3.2), gridspec_kw={"width_ratios": [1, 1.1], "wspace": 0.75})
    xs = np.array([-2.0, -5.0, -10.0])
    kap = ki["kappa_mass3"]["kappa"] if ki else 0.26
    ax = axs[0]
    ax.fill_between(xs, xs * (1 + 1.645 * kap), xs * (1 - 1.645 * kap), color=C[0], alpha=0.12, lw=0,
                    label=f"±1.645 κ|Δ| (κ = {kap:.2f})")
    for c in cases:
        R = sorted([t for t in T if t["case"] == c], key=lambda t: t["x"])
        ax.plot([t["rel_change_true_pct"] for t in R], [t["rel_change_hat_pct"] for t in R], "o-", ms=3, lw=0.9,
                color=C[0], label="Misspecified model (one line per case)" if c == cases[-1] else None)
    ax.plot(xs, xs, color=INK, lw=1.0, ls="--", label="Identity (correct model)")
    ax.set_xlabel("True change of $k_{B0}$ (%)")
    ax.set_ylabel("Estimated change (%)")
    ax.set_title("Large-sample relative change", color=INK)
    ax.legend(loc="upper left", fontsize=6.5)
    ax = axs[1]
    lab = {"axle_damp_x0.5": "Axle damping ×0.5", "axle_damp_x2": "Axle damping ×2", "eta_f_x0.82": "$\\eta_f$ ×0.82",
           "eta_f_x1.22": "$\\eta_f$ ×1.22", "kH0_x0.85": "$k_{H0}$ ×0.85", "kH0_x1.15": "$k_{H0}$ ×1.15",
           "kf_x0.8": "$k_f$ ×0.8", "kf_x1.2": "$k_f$ ×1.2", "unsprung_x0.95": "Unsprung mass ×0.95",
           "unsprung_x1.05": "Unsprung mass ×1.05"}
    base = {t["case"]: t["abs_bias_base_pct"] for t in T if abs(t["x"] - 0.05) < 1e-9}
    rel = {t["case"]: t["rel_change_bias_pp"] / 5.0 * 100 for t in T if abs(t["x"] - 0.05) < 1e-9}
    cs = [c for c in cases if c != "control"]
    y = np.arange(len(cs))
    ax.barh(y - 0.17, [base[c] for c in cs], height=0.32, color=C[1], label="Absolute $k_{B0}$ bias (%)")
    ax.barh(y + 0.17, [rel[c] for c in cs], height=0.32, color=C[0], label="Error of a −5% change\n(% of the change)")
    ax.set_yticks(y, [lab.get(c, c) for c in cs])
    ax.invert_yaxis()
    ax.axvline(0, color=INK2, lw=0.8)
    ax.set_xlabel("%")
    ax.set_title("Absolute vs relative error", color=INK)
    ax.legend(loc="upper center", bbox_to_anchor=(0.4, -0.18), ncol=2, fontsize=6.5)
    save(fig, "fig6_relative_change")


# ----------------------------------------------------------------------------- Fig. 7
def fig7():
    d = load("p2/scope_p2_hysteretic.json")
    if d is None:
        return print("skip fig7")
    rows = d["rows"]
    fig, ax = plt.subplots(figsize=(3.4, 2.7))
    rng = np.random.default_rng(0)
    for k, corr in enumerate((False, True)):
        ct = np.array([x for r in rows if r["corrugation"] == corr for x in r["ct23_kf"] if x is not None]) / 1e6
        wk = np.array([r["whittle_kf"] for r in rows if r["corrugation"] == corr]) / 1e6
        x0 = 2 * k
        n_hi = int(np.sum(ct > 50))
        if n_hi:
            ax.annotate(f"{n_hi} per-pass values > 50", (x0 - 0.3, 42), ha="left", fontsize=6.5, color=INK2)
        ax.scatter(x0 + rng.uniform(-0.25, 0.25, ct.size), ct, s=8, color=C[1], alpha=0.6, lw=0,
                   label="Per-pass peak fit (CT23)" if k == 0 else None)
        ax.scatter(x0 + 1 + rng.uniform(-0.25, 0.25, wk.size), wk, s=10, color=C[0], lw=0,
                   label="Multi-pass Whittle (8 passes)" if k == 0 else None)
    ax.axhline(7.7, color=INK2, lw=0.8, ls="--", label="True 7.7 MN/m$^2$")
    ax.set_yscale("log")
    ax.set_ylim(3, 50)
    ax.set_yticks([4, 6, 8, 10, 15, 20, 30], ["4", "6", "8", "10", "15", "20", "30"])
    ax.minorticks_off()
    ax.set_xticks([0.5, 2.5], ["Clean roughness", "Corrugation near P2"])
    ax.set_ylabel("$k_f$ estimate (MN/m$^2$)")
    ax.legend(loc="upper left", bbox_to_anchor=(0, 0.93))
    save(fig, "fig7_p2_validation")


if __name__ == "__main__":
    for fn in (fig1, fig2, fig3, fig4, fig5, fig6, fig7):
        fn()
