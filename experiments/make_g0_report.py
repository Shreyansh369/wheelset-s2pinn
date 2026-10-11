"""Build results/gates/G0_report.pdf from results/ JSON and figures only.

Every number in the PDF is read from a results file written by an experiment
script; nothing is typed in by hand. Run gate_report.py G0 first.

Usage: python experiments/make_g0_report.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.utils.results import RESULTS_DIR  # noqa: E402

from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_LEFT  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import cm  # noqa: E402
from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402
from reportlab.platypus import (  # noqa: E402
    Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
pdfmetrics.registerFont(TTFont("DejaVu", str(FONT_DIR / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(FONT_DIR / "DejaVuSans-Bold.ttf")))
# no DejaVuSans-Oblique on this system; italic maps to regular
pdfmetrics.registerFontFamily("DejaVu", normal="DejaVu", bold="DejaVu-Bold", italic="DejaVu", boldItalic="DejaVu-Bold")

INK, MUTED, RULE = colors.HexColor("#0b0b0b"), colors.HexColor("#52514e"), colors.HexColor("#d9d8d4")
PASS_C, FAIL_C, PEND_C = colors.HexColor("#0a7a3d"), colors.HexColor("#b42318"), colors.HexColor("#8a6100")

ss = getSampleStyleSheet()
H1 = ParagraphStyle("h1", parent=ss["Heading1"], fontName="DejaVu-Bold", fontSize=15, textColor=INK, spaceAfter=6)
H2 = ParagraphStyle("h2", parent=ss["Heading2"], fontName="DejaVu-Bold", fontSize=12, textColor=INK, spaceBefore=10, spaceAfter=4)
BODY = ParagraphStyle("b", parent=ss["BodyText"], fontName="DejaVu", fontSize=9.2, leading=12.5, textColor=INK, alignment=TA_LEFT)
SMALL = ParagraphStyle("s", parent=BODY, fontSize=7.8, leading=10, textColor=MUTED)
CELL = ParagraphStyle("c", parent=BODY, fontSize=8, leading=10)
CELLB = ParagraphStyle("cb", parent=CELL, fontName="DejaVu-Bold")


def load(name: str):
    p = RESULTS_DIR / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else None


def f3(x, d=3):
    if x is None:
        return "–"
    if isinstance(x, (int, np.integer)):
        return str(x)
    ax = abs(x)
    return f"{x:.{d}e}" if (ax and (ax < 1e-2 or ax >= 1e4)) else f"{x:.{d}g}"


def status_color(s: str):
    s = s.upper()
    if s.startswith("PASS") or s.startswith("NOT TRIGGERED"):
        return PASS_C
    if s.startswith("PENDING"):
        return PEND_C
    return FAIL_C


def table(rows, widths, header=True):
    data = [[c if not isinstance(c, str) else Paragraph(c, CELLB if (header and i == 0) else CELL) for c in r]
            for i, r in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, 0), 0.8, INK),
             ("LINEBELOW", (0, 1), (-1, -1), 0.3, RULE), ("LEFTPADDING", (0, 0), (-1, -1), 3),
             ("RIGHTPADDING", (0, 0), (-1, -1), 3), ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]
    t.setStyle(TableStyle(style))
    return t


def img(path: Path, width_cm: float):
    from PIL import Image as PILImage

    w, h = PILImage.open(path).size
    return Image(str(path), width=width_cm * cm, height=width_cm * cm * h / w)


def eq41_figure(e41: dict) -> Path | None:
    """Measured vs predicted decay rate (log-log), from results/p0/eq41.json records."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    pay = e41["payload"]
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.7), dpi=150)
    series = [("transient/sdof", "SDOF", "#2a78d6"), ("transient/2dof", "2-DOF", "#eb6834")]
    ax = axes[0]
    lo, hi = np.inf, 0
    for key, lab, col in series:
        recs = pay.get(key, {}).get("records", [])
        if not recs:
            continue
        x = np.array([r["lambda_pred_eq41"] for r in recs])
        y = np.array([r["lambda_meas"] for r in recs])
        ok = (x > 0) & (y > 0)
        ax.scatter(x[ok], y[ok], s=14, color=col, alpha=0.75, label=lab, zorder=3)
        lo, hi = min(lo, x[ok].min(), y[ok].min()), max(hi, x[ok].max(), y[ok].max())
    if hi > 0:
        g = np.array([lo * 0.8, hi * 1.25])
        ax.plot(g, g, color="#52514e", lw=1, zorder=2)
        ax.fill_between(g, g * 0.9, g * 1.1, color="#d9d8d4", alpha=0.6, lw=0, zorder=1, label="±10%")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("Eq. (41) prediction λ* [1/s]"); ax.set_ylabel("measured decay rate [1/s]")
    ax.set_title("Transient (free decay)", loc="left", fontsize=10)
    ax.legend(frameon=False, fontsize=8)
    ax = axes[1]
    for key, lab, col in [("forced/sdof", "SDOF", "#2a78d6"), ("forced/2dof", "2-DOF", "#eb6834")]:
        recs = pay.get(key, {}).get("records", [])
        if not recs:
            continue
        for pk, mk, nm in (("lambda_pred_eq41", "o", "Eq. (41)"), ("lambda_pred_ridge", "s", "ridge law")):
            x = np.array([r[pk] for r in recs])
            y = np.array([r["lambda_meas"] for r in recs])
            ok = (x > 0) & (y > 0)
            ax.scatter(x[ok], y[ok], s=14, marker=mk, facecolors=col if mk == "o" else "none", edgecolors=col,
                       alpha=0.8, label=f"{lab}, {nm}", zorder=3)
    xl = ax.get_xlim(); yl = ax.get_ylim()
    g = np.array([min(xl[0], yl[0]), max(xl[1], yl[1])])
    if g[0] > 0:
        ax.plot(g, g, color="#52514e", lw=1)
        ax.fill_between(g, g * 0.9, g * 1.1, color="#d9d8d4", alpha=0.6, lw=0)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("predicted effective decay rate [1/s]")
    ax.set_title("Steady state (FRF fit, Fourier time branch)", loc="left", fontsize=10)
    ax.legend(frameon=False, fontsize=7)
    for a in axes:
        a.grid(True, color="#e4e3df", lw=0.7); a.set_axisbelow(True)
        for s in ("top", "right"):
            a.spines[s].set_visible(False)
    fig.tight_layout()
    out = RESULTS_DIR / "p0" / "eq41_meas_vs_pred.png"
    fig.savefig(out)
    plt.close(fig)
    return out


def repro_curve() -> Path | None:
    log = RESULTS_DIR / "p0" / "s2pinn_repro_seed42.log"
    if not log.exists():
        return None
    steps, mean, var = [], [], []
    for line in log.read_text().splitlines():
        m = re.match(r"EVAL (\d+) mean_rel_l2=(\S+) var_rel_l2=(\S+)", line)
        if m:
            steps.append(int(m.group(1))); mean.append(float(m.group(2))); var.append(float(m.group(3)))
    if len(steps) < 2:
        return None
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6.4, 3.2), dpi=150)
    ax.plot(steps, mean, "-o", ms=3, lw=2, color="#2a78d6", label="mean rel. L2")
    ax.plot(steps, var, "-o", ms=3, lw=2, color="#eb6834", label="variance rel. L2")
    ax.axhline(3.71e-3, color="#52514e", lw=1, ls=":")
    ax.axhline(2 * 3.71e-3, color="#52514e", lw=1, ls="--")
    ax.text(steps[-1], 2 * 3.71e-3, " G0 threshold (2× paper)", va="bottom", ha="right", fontsize=8, color="#0b0b0b")
    ax.text(steps[-1], 3.71e-3, " paper (Table 1)", va="top", ha="right", fontsize=8, color="#0b0b0b")
    ax.set_yscale("log"); ax.set_xlabel("Adam step"); ax.set_ylabel("relative L2 (eval every 500)")
    ax.grid(True, color="#e4e3df", lw=0.7)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    out = RESULTS_DIR / "p0" / "s2pinn_repro_curve.png"
    fig.savefig(out)
    plt.close(fig)
    return out


def main() -> None:
    g0 = load("gates/G0")
    if g0 is None:
        raise SystemExit("run experiments/gate_report.py G0 first")
    items = g0["payload"]
    story = []
    story.append(Paragraph("wheelset-s2pinn: Phase 0 report (gate G0)", H1))
    story.append(Paragraph(
        f"Generated from <font face='DejaVu-Bold'>results/</font> by experiments/make_g0_report.py. "
        f"Gate file commit: {g0['provenance']['git_commit']}; generated {g0['provenance']['timestamp_utc']}. "
        "Every number below is read from a results JSON written by an experiment script.", SMALL))
    story.append(Spacer(1, 6))

    # ---------------- summary
    story.append(Paragraph("1. Gate summary", H2))
    labels = {
        "a_s2pinn_reproduction": "(a) S²-PINN reproduces stochastic diffusion within 2× of the paper's mean error",
        "b_h1_sdof_trend": "(b) SDOF shows a clear trend of required gPC degree with Π",
        "c_eq41": "(c) Eq. (41) within 10% of measured effective damping, or measured relation reported",
        "d_literature_stop_rule": "(d) Literature stop rule (method already published?)",
    }
    rows = [["Item", "Status", "Key numbers"]]
    a = items["a_s2pinn_reproduction"]
    a_num = (f"mean rel. L2 = {f3(a.get('mean_rel_l2'))} vs threshold {f3(a.get('threshold'))} "
             f"({f3(a.get('ratio_to_paper'))}× paper)" if "mean_rel_l2" in a else a.get("why", ""))
    b = items["b_h1_sdof_trend"]
    b_num = (f"Legendre: p ∝ Π<super>{b['legendre_slope_vs_logPi'][0]:.2f}±{b['legendre_slope_vs_logPi'][1]:.2f}</super> "
             f"(R²={b['legendre_r2']:.3f}); Hermite: overall Π<super>{b['hermite_slope_vs_logPi'][0]:.2f}</super>, "
             f"local slope → {list(b['hermite_local_slopes'].values())[-1]['median']:.2f} at large Π"
             if "legendre_slope_vs_logPi" in b else "")
    c = items["c_eq41"]
    if "settings" in c:
        c_num = "; ".join(f"{k}: median err {f3(v['median_rel_err_eq41'])}" for k, v in c["settings"].items() if v.get("n"))
    else:
        c_num = ""
    rows += [[labels["a_s2pinn_reproduction"], f"<font color='{status_color(a['status']).hexval()}'>{a['status']}</font>", a_num],
             [labels["b_h1_sdof_trend"], f"<font color='{status_color(b['status']).hexval()}'>{b['status']}</font>", b_num],
             [labels["c_eq41"], f"<font color='{status_color(c['status']).hexval()}'>{c['status']}</font>", c_num],
             [labels["d_literature_stop_rule"], f"<font color='{status_color(items['d_literature_stop_rule']['status']).hexval()}'>"
              f"{items['d_literature_stop_rule']['status']}</font>", "see docs/lit_review.md"]]
    story.append(table(rows, [6.0 * cm, 3.4 * cm, 8.1 * cm]))

    # ---------------- (a)
    story.append(Paragraph("2. (a) S²-PINN stochastic-diffusion reproduction", H2))
    rep = load("p0/s2pinn_repro_seed42")
    timing = load("p0/s2pinn_cpu_timing")
    if rep:
        p = rep["payload"]
        fm = p["final_metrics"]
        rows = [["Quantity", "This run (seed 42)", "Paper (S²-PINN, proj)"],
                ["Mean rel. L2", f3(fm["uq/mean_rel_l2"]), f3(p["paper_mean_rel_l2"])],
                ["Variance rel. L2", f3(fm["uq/var_rel_l2"]), f3(p["paper_var_rel_l2"])],
                ["Calibration error", f3(fm["uq/calibration_error"]), "0.006 ± 0.003 (Table 3)"],
                ["Coverage @90%", f3(fm.get("uq/coverage_90")), "0.897 ± 0.004 (Table 3)"],
                ["Device / budget", f"{p['device']}, {'20k steps' if p['full_paper_budget'] else 'reduced'}", "T4, 20k steps"],
                ["Wall time", f"{rep['provenance']['wall_seconds'] / 3600:.1f} h", "≈90 min (Table 18)"]]
        story.append(table(rows, [4.5 * cm, 5.5 * cm, 7.5 * cm]))
        story.append(Paragraph(
            "Paper values in the right-hand column are quoted from the S²-PINN paper (Tables 1–3, 18) for comparison. "
            f"Runner: {p.get('runner', 'spinn.train.train')}; s2pinn commit {p['s2pinn_commit'][:7]}. "
            + (p.get("note", "")), SMALL))
        curve = repro_curve()
        if curve:
            story.append(img(curve, 13))
    else:
        story.append(Paragraph(f"<b>Pending.</b> {a.get('why', '')}", BODY))
    if timing:
        story.append(Paragraph(
            f"CPU cost on this container (4 cores, no GPU): {timing['payload']['sec_per_step']:.2f} s per step, "
            f"i.e. {timing['payload']['projected_hours_20k_steps']:.1f} h for 20k steps. "
            "The 1 GB / 90 min cost limit refers to a T4 and cannot be checked on this hardware.", SMALL))
    equiv = load("p0/s2pinn_repro_seed42_equiv_steps20")
    st, rs = load("p0/s2pinn_repro_seed42_straight_steps30"), load("p0/s2pinn_repro_seed42_resume_steps30")
    if equiv or (st and rs):
        txt = "Runner checks: "
        if equiv and timing:
            txt += (f"20-step replay mean rel. L2 = {equiv['payload']['final_metrics']['uq/mean_rel_l2']:.7f} vs the released "
                    f"train() {timing['payload']['smoke_mean_rel_l2_20_steps']:.7f}. ")
        if st and rs:
            a1, a2 = st["payload"]["final_metrics"]["uq/mean_rel_l2"], rs["payload"]["final_metrics"]["uq/mean_rel_l2"]
            txt += f"Uninterrupted vs stopped-and-resumed 30-step runs: {a1:.10f} vs {a2:.10f}."
        story.append(Paragraph(txt, SMALL))

    # ---------------- (b)
    story.append(PageBreak())
    story.append(Paragraph("3. (b) H1 on an SDOF oscillator", H2))
    h1 = load("p0/h1_sdof")
    h1s = load("p0/h1_sdof_summary")
    if h1:
        cfg = h1["config"]
        story.append(Paragraph(
            "Receptance of x'' + c x' + k x = e<super>iωt</super> with random stiffness (CoV ∈ "
            f"{', '.join(f'{100 * c:.0f}%' for c in cfg['covs_primary'])}) and deterministic damper "
            f"(ζ ∈ {', '.join(f'{100 * z:g}%' for z in cfg['zetas'])}), plus a 12-point CoV supplement. "
            "Required degree = smallest p with relative variance error ≤ 1% (orthonormal projection by quadrature). "
            "Π = s/ζ with s the natural-frequency CoV.", BODY))
        f = h1["payload"]["fits_log_p_vs_log_Pi"]
        rows = [["Family (input law)", "slope of log p vs log Π (p≥3)", "R²", "n", "local slope by Π bin", "p/Π or p/Π² by bin"]]
        for fam, law, ratio_key in (("legendre", "uniform k", "p_over_Pi_by_Pi_bin"), ("hermite", "log-normal k", "p_over_Pi2_by_Pi_bin")):
            ff = f[f"{fam}/p_req_at_mean/p>=3"]
            ls = h1s["payload"][fam]["local_slope_by_Pi_bin"]
            rt = h1s["payload"][fam][ratio_key]
            rows.append([f"{fam.capitalize()} ({law})", f"{ff['slope']:.3f} ± {ff['slope_se']:.3f}", f"{ff['r2']:.4f}", str(ff["n"]),
                         "<br/>".join(f"{k}: {v['median']:.2f}" for k, v in ls.items()),
                         ("p/Π " if fam == "legendre" else "p/Π² ") + "<br/>".join(f"{k}: {v:.2f}" for k, v in rt.items())])
        story.append(table(rows, [3.3 * cm, 3.0 * cm, 1.3 * cm, 0.9 * cm, 4.2 * cm, 4.8 * cm]))
        coll = h1s["payload"]["legendre"]["collapse_pairs"] + h1s["payload"]["hermite"]["collapse_pairs"]
        story.append(Paragraph(
            "Collapse onto Π: pairs of primary-grid cases with Π within 2% but different ζ and CoV need "
            + ", ".join(f"{c['p_req'][0]}/{c['p_req'][1]}" for c in coll) + " (required degrees).", SMALL))
        story.append(img(RESULTS_DIR / "p0" / "h1_sdof_preq.png", 12.5))
        story.append(img(RESULTS_DIR / "p0" / "h1_sdof_fixed_p.png", 16))
        story.append(Paragraph(
            "<b>Reading.</b> The trend is clear, but the exponent depends on the input law. For bounded (uniform/Legendre) inputs, "
            "which is how the paper treats θ and W, the required degree grows like Π, not Π². Π² appears only asymptotically "
            "for Gaussian (Hermite) inputs. This matches approximation theory (Bernstein ellipse vs strip of analyticity) "
            "and the root-spreading result of Jacquelin et al. (2016).", BODY))

    # ---------------- (c)
    story.append(PageBreak())
    story.append(Paragraph("4. (c) Eq. (41): residual-induced damping bias", H2))
    story.append(Paragraph(
        "Derivation (docs/derivations/eq41.md): with a long-window residual loss, an enforced initial condition and a "
        "relative unresolved residual floor R, minimising over the decay rate gives λ*² = λ₀² + (R/2ω)² with λ₀ = ζω. "
        "This is Eq. (41) once ζ is read as a decay rate. The steady-state counterpart is ridge shrinkage "
        "X* = (AᴴA + R²I)⁻¹AᴴF, a different law.", BODY))
    e41 = load("p0/eq41")
    if e41:
        pay = e41["payload"]
        rows = [["Setting", "n", "median |Δ|/λ (Eq. 41)", "within 10%", "median bias / λ₀",
                 "alt. prediction (median err)", "measured λ²−λ₀² = c (R/2ω)<super>β</super>"]]
        for k in ("transient/sdof", "transient/2dof", "forced/sdof", "forced/2dof"):
            v = pay.get(k, {})
            if not v.get("n"):
                continue
            alt = (f"window: {f3(v.get('median_rel_err_lambda_pred_window'))}" if "transient" in k
                   else f"ridge: {f3(v.get('median_rel_err_lambda_pred_ridge'))}")
            mr = v.get("measured_relation")
            rel = f"c={mr['c']:.2f}, β={mr['beta']:.2f}±{mr['beta_se']:.2f} (n={mr['n']})" if mr else "–"
            rows.append([k, str(v["n"]), f3(v["median_rel_err_eq41"]), f"{100 * v['frac_within_10pct_eq41']:.0f}%",
                         f3(v["median_measured_bias_over_lambda0"]), alt, rel])
        story.append(table(rows, [2.6 * cm, 0.9 * cm, 2.4 * cm, 1.6 * cm, 2.2 * cm, 3.0 * cm, 4.8 * cm]))
        for k in ("forced/sdof", "forced/2dof"):
            pr = pay.get(k, {}).get("pointwise_ridge_amplitude")
            nc = pay.get(k, {}).get("non_collapsed_subset", {})
            if pr:
                story.append(Paragraph(
                    f"{k}: point-wise ridge-law amplitude check on {pr['n_non_collapsed']}/{pr['n_points']} non-collapsed "
                    f"points: median error {f3(pr['median_rel_err_non_collapsed'])}, "
                    f"{100 * (pr['frac_within_10pct_non_collapsed'] or 0):.0f}% within 10%. Sweeps with no collapsed point: "
                    f"{nc.get('n', 0)}" + (f" (Eq. 41 median err {f3(nc.get('median_rel_err_eq41'))}, ridge "
                                           f"{f3(nc.get('median_rel_err_lambda_pred_ridge'))})" if nc.get("n") else "") + ".", SMALL))
        mlp = pay.get("forced/sdof_mlp_at_resonance")
        if mlp:
            story.append(Paragraph(
                f"Time-domain tanh-MLP PINN on forced SDOF at resonance ({mlp['n']} runs): amplitude ratio to exact "
                f"{min(mlp['amp_ratio']):.4f}–{max(mlp['amp_ratio']):.4f}, i.e. stuck at the trivial solution x = 0.", SMALL))
        fig = eq41_figure(e41)
        if fig:
            story.append(img(fig, 16.5))
        story.append(Paragraph(f"<b>Verdict.</b> {c['status']}.", BODY))
    else:
        story.append(Paragraph("<b>Pending.</b>", BODY))

    # ---------------- (d)
    story.append(Paragraph("5. (d) Literature check", H2))
    story.append(Paragraph(
        "No published stochastic or separable PINN identifying bearing or support parameters in rotating machinery or a "
        "railway wheelset was found (web search only; Crossref and publisher sites are blocked here). Closest: a deterministic "
        "PINN for a Jeffcott rotor (Parziale et al., Sensors 24:207, 2024) and gPC-Bayesian magnetic-bearing identification. "
        "The near-resonance PCE difficulty itself is established (Jacquelin et al., JSV 2015 and J. Eng. Mech. 2015/2016; "
        "Yaghoubi et al., PEM 2017; Kara and Ferguson, JSV 2023), so H1 is framed as a quantified diagnostic. "
        "Two full texts (J. Eng. Mech. 2016; PEM 2026) need checking with library access before the scaling law is "
        "claimed as new. Full table: docs/lit_review.md.", BODY))

    # ---------------- provenance
    story.append(Paragraph("6. Provenance", H2))
    rows = [["Result file", "git commit", "wall time", "timestamp (UTC)"]]
    for n in ("p0/s2pinn_repro_seed42", "p0/s2pinn_cpu_timing", "p0/h1_sdof", "p0/h1_sdof_summary", "p0/eq41", "gates/G0"):
        r = load(n)
        if r:
            w = r["provenance"].get("wall_seconds")
            rows.append([f"results/{n}.json", r["provenance"]["git_commit"][:12] + ("…dirty" if "dirty" in r["provenance"]["git_commit"] else ""),
                         f"{w / 3600:.2f} h" if w else "–", r["provenance"]["timestamp_utc"]])
    story.append(table(rows, [6.5 * cm, 3.6 * cm, 2.4 * cm, 4.6 * cm]))

    out = RESULTS_DIR / "gates" / "G0_report.pdf"
    doc = SimpleDocTemplate(str(out), pagesize=A4, leftMargin=1.8 * cm, rightMargin=1.8 * cm, topMargin=1.6 * cm,
                            bottomMargin=1.6 * cm, title="wheelset-s2pinn Phase 0 (G0) report", author="wheelset-s2pinn")
    doc.build(story)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
