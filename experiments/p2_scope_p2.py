"""Task (e), quick scope check: multi-pass Whittle estimation of P2 track stiffness vs the per-pass peak fit
of Carrigan & Talbot (2023, CT23), on a setup modelled on their simulations, with their failure mode
(Tables 3-4): a corrugation peak near the P2 resonance at off-nominal speed.

Setup (all CT23 values from config/track.yaml / CT23 Table 1 and Sec. 5.1):
* vehicle: 12 lumped wheels (CT23 Fig. 5 layout), m_w = 400 kg, k1 = 1.59 MN/m, c1 = 3 kN s/m,
  kH = 900 MN/m; ABA = vertical acceleration of wheel 5;
* "truth" track (generator): BS113A Timoshenko rail on a continuous foundation, either CT23's analysis
  model (hysteretic kf = 7.7 MN/m^2, eta 0.2; primary, isolates the corrugation failure mode) or their
  simulator's fractional-derivative foundation beta(w) = nu w^alpha exp(i alpha pi / 2), nu = 3.9 MN/m^2,
  alpha = 1/8 (CT23 Eq. 26; 7.7 MN/m^2 at 35 Hz; adds model-form mismatch for both estimators).
  Unlike CT23's simulator, the rail is continuously supported and the response is the
  frequency-domain steady state (no pinned-pinned effect, no time stepping);
* both estimators fit CT23's analysis model: hysteretic foundation kf (1 + 0.2 i), Timoshenko rail;
* roughness: ISO 3095:2013 limit shape (extrapolated log-linearly from the 0.315-0.4 m bands to 1 m,
  as CT23 did), plus a corrugation bump of +15 dB on the sub-bands centred within 330-370 mm;
* passes: 62 m records (CT23 section length) at speeds uniform 13-21 m/s, SNR 40 dB; 8 passes per
  section, 20 sections.
CT23 method (Sec. 3.2): Welch PSD (4 m Hann segments, 50% overlap), first PSD peak with prominence
>= 5 dB (peaks >= 60 Hz apart), fit region 12 dB down either side within 0.8-1.25 f_peak, minimise
sum (sqrt(S_aa) - a w |H|)^2 over (a, kf) (b = -1), |H|^2 = sum_k |A_jk|^2 (CT23 Eq. 7), start from Eq. 13.
Multi-pass: the Whittle likelihood of src/inverse/multipass.py over all 8 passes of a section, kf
the only global parameter, one free roughness level per sub-band (K = 4 per one-third octave), cross
terms kept, band 20-150 Hz, debiased (exact expected periodogram; see MultiPassWhittle).
"""

from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "1"

import json  # noqa: E402
import math  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
from scipy.optimize import minimize  # noqa: E402
from scipy.signal import find_peaks, welch  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.p1_bound_robustness import ISO3095_FIG2_DB  # noqa: E402
from src.inverse.multipass import FS, Family, MultiPassWhittle, Table, generate_pass  # noqa: E402
from src.inverse.whittle import Roughness  # noqa: E402
from src.reference.track import RailTrack, coupled_rows, load_track_config, rail_matrix  # noqa: E402
from src.utils.results import Timer, save_result  # noqa: E402

F_LO, F_HI = 20.0, 150.0
L_SEC = 62.0
R0_EFF = L_SEC / (20 * 2 * math.pi)  # 20 "revolutions" = one 62 m section (record-length device)
CORR = (0.33, 0.37, 15.0)            # corrugation sub-bands (m) and level (dB)
DEBIAS = True                        # exact expected periodogram (cross terms with V/d near 1/T)


class FractionalTrack(RailTrack):
    def __init__(self, nu, alpha, **kw):
        super().__init__(kf=0.0, eta_f=0.0, **kw)
        self.nu, self.alpha = nu, alpha

    def beta(self, omega=None):
        return self.nu * np.asarray(omega, float) ** self.alpha * np.exp(1j * self.alpha * np.pi / 2)


class LumpedTrackModel:
    def __init__(self, track, layout, j, veh):
        self.track, self.layout, self.j, self.v = track, np.asarray(layout), j, veh
        self.d = self.layout - self.layout[j]

    def Aw(self, w):
        return 1.0 / (self.v["k1"] + 1j * w * self.v["c1"] - w**2 * self.v["m_w"])

    def G(self, w):
        N = self.layout.size
        Aw = np.repeat(self.Aw(w)[:, None], N, 1)
        rows = coupled_rows(Aw, self.v["kH"], rail_matrix(w, self.layout, self.track), self.layout, self.j)
        return -(w**2)[:, None] * Aw * rows           # wheel acceleration per unit roughness, per term

    def H_fn(self, V, fgrid):
        G = self.G(2 * np.pi * fgrid)

        def H(f):
            out = np.zeros(np.size(f), complex)
            for k in range(G.shape[1]):
                out += (np.interp(f, fgrid, G[:, k].real) + 1j * np.interp(f, fgrid, G[:, k].imag)) \
                    * np.exp(1j * 2 * np.pi * f * self.d[k] / V)
            return out
        return H

    def H_disp_incoherent(self, w):
        """CT23 Eq. (7): |H|^2 = sum_k |A_jk|^2 (displacement), cross terms omitted."""
        return np.sqrt(np.sum(np.abs(self.G(w) / (-(w**2))[:, None]) ** 2, 1))


class KfFamily(Family):
    names = ("kf",)

    def __init__(self, rail: dict, layout, j, veh, eta=0.2, f_grid=None):
        self.rail, self.layout, self.j, self.veh, self.eta = rail, layout, j, veh, eta
        self.fixed = {}
        self.f = np.arange(F_LO - 6, F_HI + 1.0, 0.25) if f_grid is None else f_grid

    def model(self, kf):
        return LumpedTrackModel(RailTrack(kf=kf, eta_f=self.eta, **self.rail), self.layout, self.j, self.veh)

    def table(self, theta):
        m = self.model(theta["kf"])
        G = m.G(2 * np.pi * self.f)
        return Table(np.log([1.0, 2.0]), self.f, np.stack([G, G]), m.d.copy())


def ct23_fit(y, V, fam: KfFamily):
    """CT23 Sec. 3.2 per-pass track-stiffness fit. Returns kf or nan if no peak is found."""
    nper = int(round(4.0 / V * FS))
    f, S = welch(y, fs=FS, window="hann", nperseg=nper, noverlap=nper // 2, scaling="density")
    band = (f >= F_LO) & (f <= F_HI)
    f, S = f[band], S[band]
    db = 10 * np.log10(S)
    pk, _ = find_peaks(db, prominence=5.0, distance=max(int(60.0 / (f[1] - f[0])), 1))
    if pk.size == 0:
        return float("nan"), float("nan")
    p = pk[0]
    fp = f[p]
    lo, hi = p, p
    while lo > 0 and db[lo - 1] > db[p] - 12 and f[lo - 1] >= 0.8 * fp:
        lo -= 1
    while hi < f.size - 1 and db[hi + 1] > db[p] - 12 and f[hi + 1] <= 1.25 * fp:
        hi += 1
    fr, Sr = f[lo:hi + 1], S[lo:hi + 1]
    w = 2 * np.pi * fr
    r, v = fam.rail, fam.veh
    wn = 2 * np.pi * fp
    EI, rA = r["E"] * r["I"], r["rho"] * r["A"]
    q = (v["m_w"] * wn**2 - v["k1"]) / (1 - v["m_w"] * wn**2 / v["kH"])
    kf0 = max(rA * wn**2 + 0.25 * EI ** (-1 / 3) * max(q, 1e-9) ** (4 / 3), 1e5)  # CT23 Eq. (13)
    a0 = float(np.mean(np.sqrt(Sr)))

    def obj(x):
        m = fam.model(math.exp(x[1]))
        Hd = m.H_disp_incoherent(w)
        return float(np.sum((np.sqrt(Sr) - math.exp(x[0]) * w * Hd) ** 2))
    x0 = [math.log(a0 / max(np.mean(w * fam.model(kf0).H_disp_incoherent(w)), 1e-30)), math.log(kf0)]
    res = minimize(obj, x0, method="Nelder-Mead", options={"xatol": 1e-6, "fatol": 1e-14, "maxiter": 2000})
    return float(math.exp(res.x[1])), float(fp)


def main(truth_kind: str = "hysteretic"):
    cfg = load_track_config()
    rail = {k: cfg["rail_BS113A"][k] for k in ("E", "G", "kappa", "rho", "A", "I")}
    veh = {k: cfg["vehicle_CT23"][k] for k in ("m_w", "k1", "c1", "kH")}
    pos = np.array(cfg["layout_CT23"]["positions"])
    j = int(cfg["layout_CT23"]["instrumented_index"])
    if truth_kind == "fractional":
        truth_track = FractionalTrack(nu=cfg["foundation"]["fractional_nu_resilient"], alpha=cfg["foundation"]["fractional_alpha"], **rail)
    else:  # CT23's own analysis model: hysteretic kf = 7.7 MN/m^2 (resilient), eta 0.2
        truth_track = RailTrack(kf=cfg["foundation"]["resilient_kf"], eta_f=cfg["foundation"]["eta_f"], **rail)
    truth = LumpedTrackModel(truth_track, pos, j, veh)
    fam = KfFamily(rail, pos, j, veh)
    # roughness: ISO 3095 extended to 1 m, K = 4 sub-bands per third octave
    bands = dict(ISO3095_FIG2_DB)
    slope = ISO3095_FIG2_DB[0.4] - ISO3095_FIG2_DB[0.315]
    for i, lam in enumerate((0.5, 0.63, 0.8, 1.0)):
        bands[lam] = ISO3095_FIG2_DB[0.4] + slope * (i + 1)
    b = np.array(sorted(bands))
    rough = Roughness(b, np.array([bands[x] for x in b]), K=4)
    sub_lam = 2 * np.pi / (rough.om_lo * np.exp((np.arange(rough.n_sub) + 0.5) * math.log(2 ** (1 / 3)) / 4))
    g_corr = np.where((sub_lam >= CORR[0]) & (sub_lam <= CORR[1]), 10 ** (CORR[2] / 10), 1.0)
    fgrid = np.arange(F_LO - 6, F_HI + 1.0, 0.25)
    rows = []
    with Timer() as tm:
        # reference: effective hysteretic kf of the fractional truth, from both methods on clean data at 20 m/s
        rng = np.random.default_rng(0)
        clean = [generate_pass(truth.H_fn(20.0, fgrid), rough, np.ones(rough.n_sub), 20.0, R0_EFF, 40.0, rng,
                               f_lo=F_LO, f_hi=F_HI, return_y=True) for _ in range(8)]
        kf_ct_clean = float(np.nanmedian([ct23_fit(p["y"], 20.0, fam)[0] for p in clean]))
        for sec in range(20):
            rng = np.random.default_rng(np.random.SeedSequence([20261012, sec]))
            Vs = rng.uniform(13.0, 21.0, 8)
            for corr in (False, True):
                g = g_corr if corr else np.ones(rough.n_sub)
                P = [generate_pass(truth.H_fn(V, fgrid), rough, g, V, R0_EFF, 40.0, rng, f_lo=F_LO, f_hi=F_HI,
                                   return_y=True) for V in Vs]
                ct = [ct23_fit(p["y"], p["V"], fam) for p in P]
                est = MultiPassWhittle([{k: v for k, v in p.items() if k != "y"} for p in P], np.ones(8), 0.03, rough, fam,
                                       debias=DEBIAS, support=(F_LO - 5, F_HI))
                r = est.fit(np.log([10e6]))
                pi = est.profile_interval(0)
                rows.append({"section": sec, "corrugation": corr, "speeds": Vs.tolist(),
                             "ct23_kf": [c[0] for c in ct], "ct23_peak_hz": [c[1] for c in ct],
                             "whittle_kf": math.exp(r["phi"][0]), "whittle_se_log": r["se_log"][0],
                             "whittle_profile90": [math.exp(pi["lo"]), math.exp(pi["hi"])], "converged": r["converged"]})
                print(f"sec={sec} corr={corr} CT23 kf (MN/m2) " + " ".join(f"{x/1e6:.1f}" for x in rows[-1]["ct23_kf"])
                      + f" | multi-pass {rows[-1]['whittle_kf']/1e6:.2f} (se {r['se_log'][0]:.3f})", flush=True)
    # summary
    summ = {}
    ref = None
    for corr in (False, True):
        R = [r for r in rows if r["corrugation"] == corr]
        ct = np.array([x for r in R for x in r["ct23_kf"]])
        wk = np.array([r["whittle_kf"] for r in R])
        if not corr:
            ref = float(np.median(wk))
        summ["corrugation" if corr else "clean"] = {
            "ct23_median_MN": float(np.nanmedian(ct) / 1e6),
            "ct23_frac_outside_x0.7_x1.43_of_ref": float(np.mean((ct < ref / 1.43) | (ct > ref * 1.43) | np.isnan(ct))),
            "ct23_range_MN": [float(np.nanmin(ct) / 1e6), float(np.nanmax(ct) / 1e6)],
            "ct23_nan_frac": float(np.mean(np.isnan(ct))),
            "whittle_median_MN": float(np.median(wk) / 1e6), "whittle_range_MN": [float(wk.min() / 1e6), float(wk.max() / 1e6)],
            "whittle_rel_spread_sd": float(np.std(np.log(wk))),
            "whittle_profile_covers_clean_ref": float(np.mean([r["whittle_profile90"][0] <= ref <= r["whittle_profile90"][1] for r in R]))}
    summ["reference_kf_MN"] = {"whittle_clean_median": ref / 1e6, "ct23_clean_20ms_median": kf_ct_clean / 1e6,
                               "truth_beta_abs_at_35Hz": float(abs(truth_track.beta(2 * np.pi * 35.0)) / 1e6),
                               "truth_kind": truth_kind}
    print(json.dumps(summ, indent=1))
    save_result(f"p2/scope_p2_{truth_kind}" + ("" if DEBIAS else "_binsampled"), {"rows": rows, "summary": summ}, cfg={
        "vehicle": veh, "rail": rail, "layout": pos.tolist(), "truth_foundation": truth_kind + " (hysteretic: kf 7.7 MN/m^2, eta 0.2; fractional: nu 3.9e6, alpha 1/8; CT23)",
        "fit_model": "hysteretic kf, eta 0.2, Timoshenko rail", "debiased_whittle": DEBIAS, "corrugation": CORR, "speeds_ms": [13, 21],
        "passes_per_section": 8, "sections": 20, "section_m": L_SEC, "band_hz": [F_LO, F_HI], "snr_db": 40},
        seed=20261012, wall_seconds=tm.seconds)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "hysteretic")
