"""Validation Monte Carlo runs, chunked so that every process finishes well inside 2 h.

--kappa  : fresh relative-change Monte Carlo for the co-estimating fit (k_B0, c_B, k_f, k_H0 per period)
           with all five misspecifications drawn at random (RANGES of p2_model_form_mw). k_f is drawn
           log-normally (sigma 0.35) by stratified sampling: replicate j uses the quantile (pi_j + 0.5)/n of
           a random permutation pi, so the n draws cover the distribution evenly and the top stratum reaches
           x2.2 (n = 40). The other four are drawn i.i.d. log-normal. True change x ~ U(2%, 10%) decrease.
           Replicates 40-43 are stress cases with k_f fixed at x2.0, 2.3, 2.6, 3.0 (other draws random);
           they are reported separately and do not enter the coverage estimate.
           Rows: results/p3/kappa_coest_runs/rows.jsonl.
--drift  : drift Monte Carlo, later-period k_f x f (default 0.8), true change 0, both estimators.
           Rows: results/p3/drift_mc_runs/kf<f>.jsonl.
--bias   : bias diagnosis on the 4-wheel headline datasets (keys (42, 40, j), j < 10): the same data
           (roughness, speeds, payloads, noise draw) at another SNR, with the base estimator (0.5 Hz table,
           sub-band-attributed scoring) or the refined one (--refined: 0.25 Hz table, exact sub-band scoring).
           Rows: results/p3/bias_diag_runs/<variant>_snr<snr>.jsonl.
Every row records its wall time. Chunks: --j0, --j1 (replicate range). --summarise writes
results/p3/validation_mc.json.
"""

from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "1"

import argparse  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
from scipy.stats import norm, spearmanr  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.p1_fe_direct import START, TRUTH, WIM, cp_interval  # noqa: E402
from experiments.p2_model_form_mw import RANGES  # noqa: E402
from experiments.p2_relative_change import gen, truth  # noqa: E402
from experiments.p2_relative_coest_drift import EST, phi, setup_all  # noqa: E402
from src.analysis.multiwheel import MultiWheelFamily  # noqa: E402
from src.inverse.multipass import MultiPassWhittle  # noqa: E402
from src.utils.results import RESULTS_DIR, save_result  # noqa: E402

OUT = RESULTS_DIR / "p3"
N_KAPPA = 40
KF_STRESS = (2.0, 2.3, 2.6, 3.0)  # replicates 40-43: k_f fixed beyond the stratified range, reported separately
KAPPA_COEST = 0.044      # results/p2/relative_coest_drift.json coest_relative.kappa_coest (rounded as stated); earlier configuration
_GAIN = Path(__file__).resolve().parents[1] / "results" / "p4" / "gain_y25.json"
if _GAIN.exists() and json.loads(_GAIN.read_text())["payload"]["estimators"]["coest"].get("kappa"):
    KAPPA_COEST = json.loads(_GAIN.read_text())["payload"]["estimators"]["coest"]["kappa"]   # frozen configuration, empty band
KAPPA_NOMINAL = 0.26


def _done(fp, key):
    return {key(json.loads(l)) for l in fp.read_text().splitlines() if l.strip()} if fp.exists() else set()


def _append(fp, row):
    fp.parent.mkdir(parents=True, exist_ok=True)
    with fp.open("a") as fh:
        fh.write(json.dumps(row) + "\n")
    print(row, flush=True)


T_START = time.perf_counter()
DEADLINE_S = 110 * 60        # a chunk never starts a replicate it cannot finish inside this budget
REP_MAX_S = [80 * 60]        # running estimate of the slowest replicate (raised: replicates take up to ~75 min under load)


def _time_left_for_rep() -> bool:
    ok = time.perf_counter() - T_START + REP_MAX_S[0] <= DEADLINE_S
    if not ok:
        print(f"deadline: stopping chunk after {time.perf_counter() - T_START:.0f} s", flush=True)
    return ok


def _fit(P, Wm, rough, fam, names, **kw):
    est = MultiPassWhittle([dict(q) for q in P], Wm, WIM, rough, fam, debias=True, **kw)
    r = est.fit(phi(names, start=True))
    return r, est


# ----------------------------------------------------------------------------- (1) kappa, co-estimating fit
def kappa_draw(j):
    perm = np.random.default_rng(np.random.SeedSequence([45, 999])).permutation(N_KAPPA)
    rng = np.random.default_rng(np.random.SeedSequence([45, j]))
    mis = {p: float(math.exp(RANGES[p][0] * rng.standard_normal())) for p in RANGES}
    mis["kf"] = (float(math.exp(RANGES["kf"][0] * norm.ppf((perm[j] + 0.5) / N_KAPPA))) if j < N_KAPPA
                 else KF_STRESS[j - N_KAPPA])
    return mis, float(rng.uniform(0.02, 0.10))


BAND = [None]      # --band empty: passes within the empty payload band (5.5-7 t, the band's primary values)


def kappa(j0, j1, tag="", zero=False):
    """kappa replicates; zero=True: the zero-change study (pre-registered 18 Oct 2026, docs/paper1_outline.md).

    zero=True keeps the misspecification draw of replicate j (kappa_draw, same seeds) and the data seeds
    (45, j, 0/1) but sets the true change to 0, so each zero-change replicate is the counterpart of kappa
    replicate j with no change. Rows: results/p3/kappa_coest_runs/rows_zero<tag>.jsonl.
    """
    if BAND[0]:
        from experiments.p4_banded import set_band
        set_band(BAND[0])
    sm, thb, rough, mw, fams, _ = setup_all()
    fp = OUT / "kappa_coest_runs" / (f"rows_zero{tag}.jsonl" if zero else f"rows{tag}.jsonl")
    done = _done(fp, lambda r: r["rep"])
    for j in range(j0, j1):
        if j in done:
            continue
        if not _time_left_for_rep():
            break
        t0 = time.perf_counter()
        mis, x = kappa_draw(j)
        if zero:
            x = 0.0
        res = {}
        for s, kt in (("base", TRUTH["kB0"]), ("later", TRUTH["kB0"] * (1 - x))):
            P, Wm, Ws, g = gen(sm, truth(thb, mis, kt), rough, mw, (45, j, 0 if s == "base" else 1))
            r, _ = _fit(P, Wm, rough, fams["coest"], EST["coest"])
            res[s] = r
        d = res["later"]["phi"][0] - res["base"]["phi"][0]
        dt = math.log(1 - x)
        se = math.hypot(res["base"]["se_log"][0], res["later"]["se_log"][0])
        _append(fp, {"rep": j, "band": BAND[0], "misspec": mis, "x": x, "D_hat": d, "D_true": dt, "se": se,
                     "abs_err_base": res["base"]["phi"][0] - math.log(TRUTH["kB0"]),
                     "phi_base": res["base"]["phi"], "phi_later": res["later"]["phi"],
                     "se_log_base": res["base"]["se_log"], "se_log_later": res["later"]["se_log"],
                     "nll_base": res["base"]["nll"], "nll_later": res["later"]["nll"],
                     "converged": res["base"]["converged"] and res["later"]["converged"],
                     "wall_s": time.perf_counter() - t0})
        REP_MAX_S[0] = max(REP_MAX_S[0], time.perf_counter() - t0)


def kappa_sing_se(tag="", reps=None):
    """Sensitivity SE for the kappa replicates with singular information (se = inf, c_B run to its bound).

    Expected-information SE of D with c_B fixed at its stored estimate in each period: the Fisher matrix of the
    co-estimating fit at the stored global estimates, the replicate's own pass design (seeds (45, j, 0/1) as
    kappa()) and the generating sub-band levels and payloads, with the c_B row and column removed. No refit.
    Rows: results/p3/kappa_coest_runs/sing_se<tag>.jsonl. With reps given (check of the approximation on
    finite-SE replicates): those replicates, rows in sing_se_check<tag>.jsonl, which summarise() does not read.
    """
    from src.utils.results import _git_commit
    if BAND[0]:
        from experiments.p4_banded import set_band
        set_band(BAND[0])
    sm, thb, rough, mw, fams, _ = setup_all()
    allr = [r for r in _rows(OUT / "kappa_coest_runs" / f"rows{tag}.jsonl") if r["rep"] < N_KAPPA]
    if reps is None:
        R = [r for r in allr if not math.isfinite(r["se"])]
        fp = OUT / "kappa_coest_runs" / f"sing_se{tag}.jsonl"
    else:
        R = [r for r in allr if r["rep"] in set(reps)]
        fp = OUT / "kappa_coest_runs" / f"sing_se_check{tag}.jsonl"
    commit = _git_commit()
    done = _done(fp, lambda r: r["rep"])
    ic = EST["coest"].index("cB")
    for r in R:
        j = r["rep"]
        if j in done:
            continue
        t0 = time.perf_counter()
        se2 = {}
        for s, kt, ph in (("base", TRUTH["kB0"], r["phi_base"]), ("later", TRUTH["kB0"] * (1 - r["x"]), r["phi_later"])):
            P, Wm, Ws, g = gen(sm, truth(thb, r["misspec"], kt), rough, mw, (45, j, 0 if s == "base" else 1))
            est = MultiPassWhittle([dict(q) for q in P], Wm, WIM, rough, fams["coest"], debias=True)
            J = est._fisher_parts(np.asarray(ph, float), np.log(g), np.log(Ws))[0]
            keep = [i for i in range(J.shape[0]) if i != ic]
            Jk = J[np.ix_(keep, keep)]
            sc = 1 / np.sqrt(np.diag(Jk))
            se2[s] = float(np.linalg.inv(Jk * np.outer(sc, sc))[0, 0] * sc[0] ** 2)
        _append(fp, {"rep": j, "se_cb_fixed": math.sqrt(se2["base"] + se2["later"]),
                     "se_base_cb_fixed": math.sqrt(se2["base"]), "se_later_cb_fixed": math.sqrt(se2["later"]),
                     "se_stored": r["se"], "band": BAND[0], "tag": tag, "git_commit": commit,
                     "wall_s": time.perf_counter() - t0})


def kappa_diag(j, tag=""):
    """Diagnostic for one kappa replicate whose base period landed far from the later one (gross failure).

    Regenerates the base-period data (seeds (45, j, 0) as kappa()), evaluates the profile negative
    log-likelihood of the co-estimating fit at the stored base solution and at the later-period solution moved
    to the base truth's k_B0 (phi_later with phi[0] -= log(1 - x)), then refits the base period from that start
    (same estimator settings as _fit, only the start differs). The stored replicate is not changed.
    Row: results/p3/kappa_coest_runs/diag_rep<j><tag>.jsonl.
    """
    from src.utils.results import _git_commit
    commit = _git_commit()
    if BAND[0]:
        from experiments.p4_banded import set_band
        set_band(BAND[0])
    sm, thb, rough, mw, fams, _ = setup_all()
    r = next(x for x in _rows(OUT / "kappa_coest_runs" / f"rows{tag}.jsonl") if x["rep"] == j)
    t0 = time.perf_counter()
    P, Wm, Ws, g = gen(sm, truth(thb, r["misspec"], TRUTH["kB0"]), rough, mw, (45, j, 0))
    est = MultiPassWhittle([dict(q) for q in P], Wm, WIM, rough, fams["coest"], debias=True)
    phi_alt = np.asarray(r["phi_later"], float).copy()
    phi_alt[0] -= math.log(1 - r["x"])
    nll_stored = float(est.profile_nll(np.asarray(r["phi_base"], float)))
    nll_alt = float(est.profile_nll(phi_alt))
    ref = est.fit(phi_alt)
    _append(OUT / "kappa_coest_runs" / f"diag_rep{j}{tag}.jsonl", {
        "rep": j, "x": r["x"], "misspec": r["misspec"], "phi_base_stored": r["phi_base"], "phi_alt_start": phi_alt.tolist(),
        "nll_stored": nll_stored, "nll_alt_start": nll_alt, "nll_lower": "stored" if nll_stored < nll_alt else "alt_start",
        "phi_refit": ref["phi"], "nll_refit": ref["nll"], "se_refit": ref["se_log"], "converged_refit": ref["converged"],
        "D_hat_stored": r["D_hat"], "D_hat_refit": r["phi_later"][0] - ref["phi"][0], "D_true": r["D_true"],
        "band": BAND[0], "tag": tag, "git_commit": commit, "wall_s": time.perf_counter() - t0})


def _code_commit() -> str:
    """HEAD, with -dirty only if code, config or docs differ from it (result rows landing meanwhile are ignored)."""
    import subprocess
    root = str(Path(__file__).resolve().parents[1])
    head = subprocess.run(["git", "-C", root, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", root, "status", "--porcelain", "--untracked-files=no", "--", ".", ":!results"],
                           capture_output=True, text=True).stdout.strip()
    return head + ("-dirty" if dirty else "")


LOG_CB_NOMINAL = math.log(6.74e3)    # config/params.yaml bearing cB nominal (6740 N s/m)


def kappa_diag_cb(tag="", reps=None):
    """Restart diagnostic for the kappa replicates with c_B at its lower bound (log c_B < 0) in either period.

    For each period at the bound (data regenerated with the seeds of kappa()), the profile NLL at the stored
    solution and two refits: (a) from the other period's solution moved to this period's k_B0 truth, when the
    other period's c_B is interior; (b) from the stored solution with log c_B reset to the nominal value.
    For each period not at the bound, the SE at the stored solution (Hessian, as in fit) so that the change can
    be re-formed from the lower-NLL solutions. Same estimator settings as _fit; the stored replicates are not
    changed (post-hoc sensitivity only). For replicate 35, start (a) of the base period is taken from
    diag_rep35<tag>.jsonl. Rows: results/p3/kappa_coest_runs/diag_cbbound<tag>.jsonl.
    """
    commit = _code_commit()
    if BAND[0]:
        from experiments.p4_banded import set_band
        set_band(BAND[0])
    sm, thb, rough, mw, fams, _ = setup_all()
    R = [r for r in _rows(OUT / "kappa_coest_runs" / f"rows{tag}.jsonl")
         if r["rep"] < N_KAPPA and (r["phi_base"][1] < 0 or r["phi_later"][1] < 0)]
    if reps is not None:
        R = [r for r in R if r["rep"] in set(reps)]
    fp = OUT / "kappa_coest_runs" / f"diag_cbbound{tag}.jsonl"
    done = _done(fp, lambda r: r["rep"])
    d35 = {x["rep"]: x for x in _rows(OUT / "kappa_coest_runs" / f"diag_rep35{tag}.jsonl")}
    ts = {x["rep"]: x for x in _rows(OUT / "kappa_coest_runs" / f"twostart{tag}.jsonl")}   # start (a) made by A1
    for r in R:
        j = r["rep"]
        if j in done:
            continue
        t0 = time.perf_counter()
        sh = math.log(1 - r["x"])             # log k_B0 truth, later minus base
        out = {}
        for s, kt, ph, oth, shift in (("base", TRUTH["kB0"], r["phi_base"], r["phi_later"], -sh),
                                      ("later", TRUTH["kB0"] * (1 - r["x"]), r["phi_later"], r["phi_base"], sh)):
            P, Wm, Ws, g = gen(sm, truth(thb, r["misspec"], kt), rough, mw, (45, j, 0 if s == "base" else 1))
            est = MultiPassWhittle([dict(q) for q in P], Wm, WIM, rough, fams["coest"], debias=True)
            phs = np.asarray(ph, float)
            f0 = float(est.profile_nll(phs))
            rec = {"at_bound": ph[1] < 0, "nll_stored": f0, "phi_stored": list(ph), "starts": {}}
            if ph[1] < 0:
                if oth[1] >= 0:
                    if j in d35 and s == "base":
                        x = d35[j]
                        rec["starts"]["other_period"] = {"nll": x["nll_refit"], "phi": x["phi_refit"], "se_log": x["se_refit"],
                                                         "converged": x["converged_refit"], "from": f"diag_rep{j}{tag}.jsonl"}
                    elif j in ts and ts[j][s]["refit"]["from"] == "computed":
                        x = ts[j][s]["refit"]
                        rec["starts"]["other_period"] = {"nll": x["nll"], "phi": x["phi"], "se_log": x["se_log"],
                                                         "converged": x["converged"], "from": f"twostart{tag}.jsonl"}
                    else:
                        st = np.asarray(oth, float).copy()
                        st[0] += shift
                        q = est.fit(st)
                        rec["starts"]["other_period"] = {"nll": q["nll"], "phi": q["phi"], "se_log": q["se_log"], "converged": q["converged"]}
                st = phs.copy()
                st[1] = LOG_CB_NOMINAL
                q = est.fit(st)
                rec["starts"]["cb_nominal"] = {"nll": q["nll"], "phi": q["phi"], "se_log": q["se_log"], "converged": q["converged"]}
            Hs = est._hessian(phs, f0)
            ev = np.linalg.eigvalsh(Hs)
            rec["se_stored"] = (np.sqrt(np.diag(np.linalg.inv(Hs))) if ev.min() > 0 else np.full(phs.size, np.inf)).tolist()
            out[s] = rec
        _append(fp, {"rep": j, "x": r["x"], "misspec": r["misspec"], "D_true": r["D_true"], "D_hat_stored": r["D_hat"],
                     "base": out["base"], "later": out["later"], "band": BAND[0], "tag": tag, "git_commit": commit,
                     "wall_s": time.perf_counter() - t0})


def kappa_diag_order(j, mode, tag=""):
    """Fit-order diagnostic for zero-change replicate j (19 Oct 2026; no estimator change).

    Refits the zero-change replicate exactly as kappa(zero=True) does (same draws, data seeds (45, j, 0/1), same
    estimator and start), but either one period alone in this fresh process (mode "base" or "later"; run each
    in its own process) or both periods in reversed order, later first (mode "reversed"). Compared against the
    stored rows by summarise() (max |delta phi| and |delta D_hat|); any difference would point to state shared
    between the two fits of one process. Rows: results/p3/kappa_coest_runs/diag_order_zero<tag>.jsonl.
    """
    commit = _code_commit()
    if BAND[0]:
        from experiments.p4_banded import set_band
        set_band(BAND[0])
    sm, thb, rough, mw, fams, _ = setup_all()
    fp = OUT / "kappa_coest_runs" / f"diag_order_zero{tag}.jsonl"
    if (j, mode) in _done(fp, lambda r: (r["rep"], r["mode"])):
        return
    mis, _ = kappa_draw(j)
    order = {"base": ["base"], "later": ["later"], "reversed": ["later", "base"]}[mode]
    t0 = time.perf_counter()
    res = {}
    for s in order:
        P, Wm, Ws, g = gen(sm, truth(thb, mis, TRUTH["kB0"]), rough, mw, (45, j, 0 if s == "base" else 1))
        r, _ = _fit(P, Wm, rough, fams["coest"], EST["coest"])
        res[s] = {"phi": r["phi"], "se_log": r["se_log"], "nll": r["nll"], "converged": r["converged"]}
    _append(fp, {"rep": j, "mode": mode, "order": order, "fits": res, "band": BAND[0], "tag": tag,
                 "git_commit": commit, "wall_s": time.perf_counter() - t0})


def kappa_two_start(tag="", reps=None):
    """Two-start sensitivity on all kappa replicates (A1; rule decided 18 Oct 2026 before its results,
    docs/paper1_outline.md). Each period is refitted from the other period's stored solution with k_B0 moved to
    this period's truth (start (a) of kappa_diag_cb), and the lower-NLL solution of {stored, refit} is kept.
    Post-hoc sensitivity only: summarise() reports coverage and inflation factor from it in a block labelled so,
    never in place of the pre-registered statistics. Refits already made by the restart diagnostic
    (diag_cbbound<tag>.jsonl, start "other_period"; diag_rep35<tag>.jsonl for the base period of replicate 35) are
    reused, not repeated. The SE at the stored solution (Hessian, as in fit) is recorded for both periods so that
    the change can be re-formed from either solution. Rows: results/p3/kappa_coest_runs/twostart<tag>.jsonl.
    """
    commit = _code_commit()
    if BAND[0]:
        from experiments.p4_banded import set_band
        set_band(BAND[0])
    sm, thb, rough, mw, fams, _ = setup_all()
    R = [r for r in _rows(OUT / "kappa_coest_runs" / f"rows{tag}.jsonl") if r["rep"] < N_KAPPA]
    if reps is not None:
        R = [r for r in R if r["rep"] in set(reps)]
    fp = OUT / "kappa_coest_runs" / f"twostart{tag}.jsonl"
    done = _done(fp, lambda r: r["rep"])
    dc = {x["rep"]: x for x in _rows(OUT / "kappa_coest_runs" / f"diag_cbbound{tag}.jsonl")}
    d35 = {x["rep"]: x for x in _rows(OUT / "kappa_coest_runs" / f"diag_rep35{tag}.jsonl")}
    for r in R:
        j = r["rep"]
        if j in done:
            continue
        if not _time_left_for_rep():
            break
        t0 = time.perf_counter()
        sh = math.log(1 - r["x"])
        out = {}
        for s, kt, ph, oth, shift in (("base", TRUTH["kB0"], r["phi_base"], r["phi_later"], -sh),
                                      ("later", TRUTH["kB0"] * (1 - r["x"]), r["phi_later"], r["phi_base"], sh)):
            st = np.asarray(oth, float).copy()
            st[0] += shift
            prev = dc.get(j, {}).get(s, {})
            P, Wm, Ws, g = gen(sm, truth(thb, r["misspec"], kt), rough, mw, (45, j, 0 if s == "base" else 1))
            est = MultiPassWhittle([dict(q) for q in P], Wm, WIM, rough, fams["coest"], debias=True)
            phs = np.asarray(ph, float)
            f0 = float(est.profile_nll(phs))
            if "other_period" in prev.get("starts", {}):
                q = dict(prev["starts"]["other_period"], **{"from": f"diag_cbbound{tag}.jsonl"})
            elif j in d35 and s == "base":
                x = d35[j]
                q = {"nll": x["nll_refit"], "phi": x["phi_refit"], "se_log": x["se_refit"], "converged": x["converged_refit"],
                     "from": f"diag_rep{j}{tag}.jsonl"}
            else:
                f = est.fit(st)
                q = {"nll": f["nll"], "phi": f["phi"], "se_log": f["se_log"], "converged": f["converged"], "from": "computed"}
            if "se_stored" in prev:
                se_st = prev["se_stored"]
            else:
                Hs = est._hessian(phs, f0)
                se_st = (np.sqrt(np.diag(np.linalg.inv(Hs))) if np.linalg.eigvalsh(Hs).min() > 0 else np.full(phs.size, np.inf)).tolist()
            out[s] = {"nll_stored": f0, "phi_stored": list(ph), "se_stored": se_st, "start": st.tolist(), "refit": q}
        _append(fp, {"rep": j, "x": r["x"], "misspec": r["misspec"], "D_true": r["D_true"], "D_hat_stored": r["D_hat"],
                     "base": out["base"], "later": out["later"], "band": BAND[0], "tag": tag, "git_commit": commit,
                     "wall_s": time.perf_counter() - t0})
        REP_MAX_S[0] = max(REP_MAX_S[0], time.perf_counter() - t0)


# ----------------------------------------------------------------------------- (3) drift MC
def drift(j0, j1, f, tag=""):
    sm, thb, rough, mw, fams, _ = setup_all()
    fp = OUT / "drift_mc_runs" / f"kf{f}{tag}.jsonl"
    done = _done(fp, lambda r: (r["estimator"], r["rep"]))
    for j in range(j0, j1):
        if all((e, j) in done for e in EST):
            continue
        if not _time_left_for_rep():
            break
        t0 = time.perf_counter()
        data = {"base": gen(sm, truth(thb, {}, TRUTH["kB0"]), rough, mw, (46, j, 0)),
                "later": gen(sm, truth(thb, {"kf": f}, TRUTH["kB0"]), rough, mw, (46, j, 1))}
        for e in EST:
            if (e, j) in done:
                continue
            t1 = time.perf_counter()
            res = {s: _fit(data[s][0], data[s][1], rough, fams[e], EST[e])[0] for s in data}
            d = res["later"]["phi"][0] - res["base"]["phi"][0]
            se = math.hypot(res["base"]["se_log"][0], res["later"]["se_log"][0])
            _append(fp, {"estimator": e, "rep": j, "f": f, "D_hat": d, "se": se, "alarm": bool(d < -1.645 * se),
                         "converged": res["base"]["converged"] and res["later"]["converged"],
                         "wall_s": time.perf_counter() - t1 + (t1 - t0 if e == "nominal" else 0.0)})
        REP_MAX_S[0] = max(REP_MAX_S[0], time.perf_counter() - t0)


# ----------------------------------------------------------------------------- (2) bias diagnosis
def bias(j0, j1, snr, refined, seed=42, kb=None, ksub=None, smooth=None):
    from experiments.p2_common import setup
    from experiments.p2_multiwheel import dataset, models
    sm, thb, rough, _ = setup()
    mw = models(sm)[0]["4"]
    fam = MultiWheelFamily(mw, thb, f_grid=np.arange(45.0, 702.0, 0.25) if refined else None)
    # tags: "base"/"refined" = the original +-30-bin kernel runs; otherwise the kernel width is explicit
    kb_eff = 30 if (kb is None and ksub is None and smooth is None) else (kb or 120)
    if ksub is None and smooth is None:
        tag = ("refined" if refined else "base") if kb is None else f"kb{kb}"
    else:
        tag = f"kb{kb_eff}" + (f"_K{ksub}" if ksub else "") + (f"_sm{smooth:g}" if smooth else "")
    import dataclasses
    rough_est = dataclasses.replace(rough, K=ksub) if ksub else rough
    fp = OUT / "bias_diag_runs" / (f"{tag}_snr{int(snr)}.jsonl" if seed == 42 else f"{tag}_snr{int(snr)}_seed{seed}.jsonl")
    done = _done(fp, lambda r: r["j"])
    lt = math.log(TRUTH["kB0"])
    for j in range(j0, j1):
        if j in done:
            continue
        t0 = time.perf_counter()
        P, Wm, Ws, g = dataset(sm, thb, rough, mw, (seed, 40, j), N=50, snr=snr)
        est = MultiPassWhittle([dict(q) for q in P], Wm, WIM, rough_est, fam, debias=True, exact_subband=refined,
                               Kb=kb_eff, smooth_sigma_db=smooth)
        r = est.fit(np.log([START["kB0"], START["cB"]]))
        crb = est.expected_fisher(np.log([TRUTH["kB0"], TRUTH["cB"]]), np.log(g) if not ksub else np.zeros(est.S), np.log(Ws))["crb_log"]
        _append(fp, {"j": j, "seed": seed, "snr_db": snr, "variant": tag, "err_log": [r["phi"][0] - lt, r["phi"][1] - math.log(TRUTH["cB"])],
                     "se_log": r["se_log"], "crb_log": crb, "converged": r["converged"], "wall_s": time.perf_counter() - t0})


# ----------------------------------------------------------------------------- summary
def _rows(fp):
    return [json.loads(l) for l in fp.read_text().splitlines() if l.strip()] if fp.exists() else []


def _covered(r, k):
    """Interval coverage of one replicate; None when the information was singular (se = inf, c_B at its bound)."""
    if not math.isfinite(r["se"]):
        return None
    return abs(r["D_hat"] - r["D_true"]) <= 1.645 * math.sqrt(r["se"] ** 2 + (k * r["D_hat"]) ** 2)


def summarise():
    out = {}
    KR = OUT / "kappa_coest_runs" / "rows_frozen.jsonl"          # frozen configuration, empty band, when present
    Rall = _rows(KR) if KR.exists() else _rows(OUT / "kappa_coest_runs" / "rows.jsonl")
    out["kappa_rows"] = KR.name if KR.exists() else "rows.jsonl"
    R = [r for r in Rall if r["rep"] < N_KAPPA]
    if Rall:
        out["kappa_coest_stress"] = [{"rep": r["rep"], "kf": r["misspec"]["kf"], "true_change_pct": -100 * r["x"],
                                      "est_change_pct": 100 * (math.exp(r["D_hat"]) - 1),
                                      "error_frac": (r["D_hat"] - r["D_true"]) / abs(r["D_true"]),
                                      "covered": _covered(r, KAPPA_COEST)}
                                     for r in sorted(Rall, key=lambda r: r["rep"]) if r["rep"] >= N_KAPPA]
    if R:
        # replicates with singular information (se = inf) have no interval: coverage, inflation and the
        # empirical kappa use the finite-SE replicates only (as the banded pairs, p4_banded); the singular
        # replicates are listed and also counted as not covered in a sensitivity line
        Rf = [r for r in R if math.isfinite(r["se"])]
        sing = sorted(r["rep"] for r in R if not math.isfinite(r["se"]))

        def cov(k):
            c = [_covered(r, k) for r in Rf]
            return sum(c), len(c)
        ks, n = cov(KAPPA_COEST)
        k0, _ = cov(0.0)
        ge = [(r["D_hat"] - r["D_true"]) / abs(r["D_true"]) for r in R]
        gef = [(r["D_hat"] - r["D_true"]) / abs(r["D_true"]) for r in Rf]
        # gross-failure rule (recorded 18 Oct 2026, docs/paper1_outline.md): |error_frac| > 1, i.e. a change error
        # larger than the change itself. Coverage and inflation keep these replicates (each counts as a miss); the
        # rms and mean change error and the attribution regression use the non-gross replicates, and the gross
        # ones are listed
        Rng = [r for r in R if abs((r["D_hat"] - r["D_true"]) / r["D_true"]) <= 1]
        gross = sorted(r["rep"] for r in R if abs((r["D_hat"] - r["D_true"]) / r["D_true"]) > 1)
        gng = [(r["D_hat"] - r["D_true"]) / abs(r["D_true"]) for r in Rng]
        worst = sorted(R, key=lambda r: -abs((r["D_hat"] - r["D_true"]) / r["D_true"]))[:5]
        # inflation of the combined interval needed for 90% coverage under simultaneous model errors: the
        # smallest r with |D_hat - D_true| <= 1.645 r sqrt(se^2 + (kappa D_hat)^2) in at least 90% of replicates
        ratio = sorted(abs(r["D_hat"] - r["D_true"]) / (1.645 * math.sqrt(r["se"] ** 2 + (KAPPA_COEST * r["D_hat"]) ** 2)) for r in Rf)
        r90 = float(ratio[math.ceil(0.9 * n) - 1])
        # sensitivity: the singular replicates with the expected-information SE at c_B fixed (kappa_sing_se);
        # inflation over all replicates, only when every singular replicate has one
        ss = {x["rep"]: x["se_cb_fixed"] for x in _rows(OUT / "kappa_coest_runs" / KR.name.replace("rows", "sing_se"))} if KR.exists() else {}
        r90_all = None
        if all(j in ss for j in sing):
            ra = sorted(abs(r["D_hat"] - r["D_true"]) / (1.645 * math.sqrt((r["se"] if math.isfinite(r["se"]) else ss[r["rep"]]) ** 2
                                                                           + (KAPPA_COEST * r["D_hat"]) ** 2)) for r in R)
            r90_all = float(ra[math.ceil(0.9 * len(R)) - 1])
        # pre-registered (decided 18 Oct 2026, before kappa reached 40/40; docs/paper1_outline.md): the conservative
        # detection-limit factor is max(inflation_for_90pct, inflation_for_90pct_all); without the sensitivity SEs
        # it is inflation_for_90pct and the text states that the singular replicates were excluded
        r90_cons = max(r90, r90_all) if r90_all is not None else r90
        out["kappa_coest"] = {
            "n": n, "n_all": len(R), "n_finite_se": n, "singular_reps": sing,
            "kappa": KAPPA_COEST, "inflation_for_90pct": r90, "inflation_rank": math.ceil(0.9 * n),
            "inflation_for_90pct_all": r90_all, "inflation_rank_all": math.ceil(0.9 * len(R)),
            "singular_se_cb_fixed": {str(j): ss.get(j) for j in sing},
            "inflation_conservative": r90_cons, "inflation_conservative_includes_singular": r90_all is not None,
            # check of the c_B-fixed approximation on finite-SE replicates with c_B away from its bound
            "sing_se_check": [{"rep": x["rep"], "ratio": x["se_cb_fixed"] / x["se_stored"]}
                              for x in _rows(OUT / "kappa_coest_runs" / KR.name.replace("rows", "sing_se_check"))] if KR.exists() else [],
            "ratio_sorted": [float(x) for x in ratio], "coverage": ks / n, "coverage_ci95": cp_interval(ks, n),
            "coverage_statistical_only": k0 / n, "coverage_statistical_only_ci95": cp_interval(k0, n),
            "coverage_singular_as_not_covered": ks / len(R), "coverage_singular_as_not_covered_ci95": cp_interval(ks, len(R)),
            "rms_change_error_frac": float(np.sqrt(np.mean(np.square(gng)))),
            "mean_change_error_frac": float(np.mean(gng)),
            "change_error_frac_n": len(Rng), "gross_reps": gross, "n_gross": len(gross),
            "rms_change_error_frac_all": float(np.sqrt(np.mean(np.square(ge)))),
            "median_abs_change_error_frac_all": float(np.median(np.abs(ge))),
            "kappa_empirical_rms": float(np.sqrt(max(np.mean(np.square(gef)) - np.mean([(r["se"] / r["D_true"]) ** 2 for r in Rf]), 0.0))),
            "kf_draw_range": [min(r["misspec"]["kf"] for r in R), max(r["misspec"]["kf"] for r in R)],
            "n_kf_ge_2": sum(r["misspec"]["kf"] >= 2 for r in R),
            "abs_bias_base_pct_rms": float(np.sqrt(np.mean([(math.exp(r["abs_err_base"]) - 1) ** 2 for r in R])) * 100),
            "worst": [{"rep": r["rep"], "misspec": r["misspec"], "true_change_pct": -100 * r["x"],
                       "est_change_pct": 100 * (math.exp(r["D_hat"]) - 1),
                       "error_frac": (r["D_hat"] - r["D_true"]) / abs(r["D_true"]),
                       "covered": _covered(r, KAPPA_COEST)}
                      for r in worst],
            "all_converged": all(r["converged"] for r in R),
            "wall_s_median": float(np.median([r["wall_s"] for r in R]))}
        # diagnostic: which model error drives the change error (error_frac does not need se); the regression on
        # the non-gross replicates, the rank correlation on all
        names = list(RANGES)
        X = np.array([[math.log(r["misspec"][p]) for p in names] for r in Rng])
        y = np.array(gng)
        Xa = np.array([[math.log(r["misspec"][p]) for p in names] for r in R])

        def ols(Xc):
            A = np.column_stack([np.ones(len(y)), Xc])
            b, *_ = np.linalg.lstsq(A, y, rcond=None)
            res = y - A @ b
            return b, 1 - float(res @ res) / float(((y - y.mean()) ** 2).sum()), res
        ia = names.index("axle_damp_scale")
        b1, r2_axle, res_axle = ols(X[:, [ia]])
        _, r2_all, _ = ols(X)
        cb_bound = sorted(r["rep"] for r in R if r["phi_base"][1] < 0 or r["phi_later"][1] < 0)
        out["kappa_coest_attribution"] = {
            "n": len(Rng), "n_all": len(R), "gross_reps": gross,
            "spearman_axle_damp_all": float(spearmanr(Xa[:, ia], ge)[0]),
            "pearson_error_frac_vs_log_factor": {p: float(np.corrcoef(X[:, i], y)[0, 1]) for i, p in enumerate(names)},
            "r2_all_five": r2_all, "r2_axle_damp_only": r2_axle, "slope_axle_damp_per_log": float(b1[1]),
            "resid_rms_error_frac_after_axle_damp": float(np.sqrt(np.mean(res_axle ** 2))),
            "cb_lower_bound_n": len(cb_bound), "cb_lower_bound_reps": cb_bound,
            "note": "c_B at its lower bound: log c_B < 0 in either period"}
        # optimizer diagnostics (post-hoc; the pre-registered statistics above keep the stored replicates)
        tg = KR.name[len("rows"):-len(".jsonl")] if KR.exists() else ""
        d35 = _rows(OUT / "kappa_coest_runs" / f"diag_rep35{tg}.jsonl")
        dg = {}
        if d35:
            x = d35[0]
            dg["rep35"] = {"nll_gap": x["nll_stored"] - x["nll_refit"], "D_hat_refit": x["D_hat_refit"],
                           "D_hat_stored": x["D_hat_stored"], "D_true": x["D_true"]}
        dc = {x["rep"]: x for x in _rows(OUT / "kappa_coest_runs" / f"diag_cbbound{tg}.jsonl")}
        if dc:
            def best(p):          # lowest-NLL solution of one period: stored or a refit
                cand = [(p["nll_stored"], p["phi_stored"], p["se_stored"], "stored")] + \
                       [(v["nll"], v["phi"], v["se_log"], k) for k, v in p["starts"].items()]
                return min(cand, key=lambda c: c[0])
            per = []
            for j, x in sorted(dc.items()):
                b, l = best(x["base"]), best(x["later"])
                gap = max(x["base"]["nll_stored"] - b[0], x["later"]["nll_stored"] - l[0])
                per.append({"rep": j, "nll_gap_max": gap, "local_optimum": gap > 10, "best_base": b[3], "best_later": l[3],
                            "D_hat_best": l[1][0] - b[1][0], "se_best": math.hypot(b[2][0], l[2][0])})
            lo = [p["rep"] for p in per if p["local_optimum"]]
            alt = {p["rep"]: p for p in per}
            # post-hoc sensitivity only: the lower-NLL solution in place of the stored one, same interval and rule
            Ra = [dict(r, D_hat=alt[r["rep"]]["D_hat_best"], se=alt[r["rep"]]["se_best"]) if r["rep"] in alt else r for r in R]
            Raf = [r for r in Ra if math.isfinite(r["se"])]
            ka = sum(_covered(r, KAPPA_COEST) for r in Raf)
            rat = sorted(abs(r["D_hat"] - r["D_true"]) / (1.645 * math.sqrt(r["se"] ** 2 + (KAPPA_COEST * r["D_hat"]) ** 2)) for r in Raf)
            dg["cbbound"] = {"n_diagnosed": len(dc), "n_cb_bound": len(cb_bound), "complete": set(dc) >= set(cb_bound),
                             "local_optimum_reps": lo, "n_local_optimum": len(lo), "threshold_nll": 10, "per_rep": per,
                             "posthoc_lower_nll": {"label": "post-hoc sensitivity; does not replace the pre-registered statistics",
                                                   "n_finite_se": len(Raf), "n_all": len(Ra), "coverage": ka / len(Raf),
                                                   "coverage_ci95": cp_interval(ka, len(Raf)),
                                                   "coverage_singular_as_not_covered": ka / len(Ra),
                                                   "inflation_for_90pct": float(rat[math.ceil(0.9 * len(Raf)) - 1])}}
        tw = {x["rep"]: x for x in _rows(OUT / "kappa_coest_runs" / f"twostart{tg}.jsonl")}
        if tw:
            # A1, two-start sensitivity (post-hoc): per period the lower-NLL of {stored, refit from the other period}
            def pick(p):
                q = p["refit"]
                return (q["phi"], q["se_log"], "refit") if q["nll"] < p["nll_stored"] else (p["phi_stored"], p["se_stored"], "stored")
            per, Rt = [], []
            for r in R:
                if r["rep"] not in tw:
                    continue
                x = tw[r["rep"]]
                b, l = pick(x["base"]), pick(x["later"])
                gap = max(x["base"]["nll_stored"] - x["base"]["refit"]["nll"], x["later"]["nll_stored"] - x["later"]["refit"]["nll"])
                d, se = l[0][0] - b[0][0], math.hypot(b[1][0], l[1][0])
                per.append({"rep": r["rep"], "kept_base": b[2], "kept_later": l[2], "nll_gap_max": gap, "D_hat": d, "se": se,
                            "D_hat_stored": r["D_hat"], "cb_bound_after": b[0][1] < 0 or l[0][1] < 0})
                Rt.append(dict(r, D_hat=d, se=se))
            Rtf = [r for r in Rt if math.isfinite(r["se"])]
            kt = sum(_covered(r, KAPPA_COEST) for r in Rtf)
            rt = sorted(abs(r["D_hat"] - r["D_true"]) / (1.645 * math.sqrt(r["se"] ** 2 + (KAPPA_COEST * r["D_hat"]) ** 2)) for r in Rtf)
            dg["two_start"] = {"label": "post-hoc sensitivity; does not replace the pre-registered statistics",
                               "rule": "each period refitted from the other period's solution (k_B0 moved to its own truth); lower NLL kept",
                               "n": len(Rt), "complete": len(Rt) == len(R), "n_finite_se": len(Rtf),
                               "n_changed": sum(p["kept_base"] == "refit" or p["kept_later"] == "refit" for p in per),
                               "n_local_optimum": sum(p["nll_gap_max"] > 10 for p in per),
                               "n_cb_bound_after": sum(p["cb_bound_after"] for p in per),
                               "coverage": kt / len(Rtf) if Rtf else None,
                               "coverage_ci95": cp_interval(kt, len(Rtf)) if Rtf else None,
                               "coverage_singular_as_not_covered": kt / len(Rt) if Rt else None,
                               "inflation_for_90pct": float(rt[math.ceil(0.9 * len(Rtf)) - 1]) if Rtf else None,
                               "inflation_rank": math.ceil(0.9 * len(Rtf)), "per_rep": per,
                               "files_reused": sorted({x[s]["refit"]["from"] for x in tw.values() for s in ("base", "later")})}
        if dg:
            out["kappa_coest_optimizer_diag"] = dg
        # zero-change study (pre-registered 18 Oct 2026, docs/paper1_outline.md, before any result): z = D_hat/se,
        # s0 = max(1, sd(z)); false-alarm rate = fraction with D_hat < -1.645 se (one-sided, decrease) with its
        # Clopper-Pearson interval; singular replicates take the c_B-fixed sensitivity SE (sing_se_zero<tag>);
        # g90 = 90th percentile (numpy default, linear) of error_frac over the kappa replicates, positive = change
        # underestimated; the conservative MDC (make_paper_numbers) = nominal banded MDC x s0 / (1 - g90)
        Z = [r for r in _rows(OUT / "kappa_coest_runs" / f"rows_zero{tg}.jsonl") if r["rep"] < N_KAPPA]
        if Z:
            ssz = {x["rep"]: x["se_cb_fixed"] for x in _rows(OUT / "kappa_coest_runs" / f"sing_se_zero{tg}.jsonl")}
            singz = sorted(r["rep"] for r in Z if not math.isfinite(r["se"]))
            Zu = [dict(r, se=r["se"] if math.isfinite(r["se"]) else ssz[r["rep"]]) for r in Z
                  if math.isfinite(r["se"]) or r["rep"] in ssz]
            z = np.array([r["D_hat"] / r["se"] for r in Zu])
            fa = int(sum(r["D_hat"] < -1.645 * r["se"] for r in Zu))
            sdz = float(np.std(z, ddof=1)) if len(z) > 1 else None
            out["zero_change"] = {
                "rows": f"rows_zero{tg}.jsonl", "n": len(Z), "n_used": len(Zu), "complete": len(Z) == N_KAPPA,
                "singular_reps": singz, "n_singular": len(singz), "singular_with_sensitivity_se": sorted(set(singz) & set(ssz)),
                "all_singular_have_se": set(singz) <= set(ssz),
                "z_sd": sdz, "z_mean": float(z.mean()), "s0": max(1.0, sdz) if sdz is not None else None,
                "false_alarms": fa, "false_alarm_rate": fa / len(Zu), "false_alarm_ci95": cp_interval(fa, len(Zu)),
                "D_hat_sd_pct": float(np.std([r["D_hat"] for r in Zu], ddof=1) * 100),
                "se_median_pct": float(np.median([r["se"] for r in Zu]) * 100),
                "g90": float(np.percentile(ge, 90)), "g90_n": len(ge),
                # the replicates with finite information only (no sensitivity SE), reported beside the rule
                "finite_only": {"n": len([r for r in Z if math.isfinite(r["se"])]),
                                "z_sd": float(np.std([r["D_hat"] / r["se"] for r in Z if math.isfinite(r["se"])], ddof=1)),
                                "z_mean": float(np.mean([r["D_hat"] / r["se"] for r in Z if math.isfinite(r["se"])])),
                                "false_alarms": int(sum(r["D_hat"] < -1.645 * r["se"] for r in Z if math.isfinite(r["se"])))},
                "false_alarm_reps": sorted(r["rep"] for r in Zu if r["D_hat"] < -1.645 * r["se"]),
                "all_converged": all(r["converged"] for r in Z),
                "wall_s_median": float(np.median([r["wall_s"] for r in Z]))}
            zc = out["zero_change"]
            zc["mdc_factor"] = zc["s0"] / (1 - zc["g90"]) if zc["s0"] is not None else None
        do = _rows(OUT / "kappa_coest_runs" / f"diag_order_zero{tg}.jsonl")
        if do and Z:
            # fit-order diagnostic: each period alone in a fresh process, and both in reversed order, against
            # the stored zero-change rows (fitted base then later in one process)
            zs = {r["rep"]: r for r in Z}
            dphi, dD, per = 0.0, 0.0, []
            for x in do:
                r = zs.get(x["rep"])
                if r is None:
                    continue
                st = {"base": r["phi_base"], "later": r["phi_later"]}
                dp = max(max(abs(a - b) for a, b in zip(x["fits"][s]["phi"], st[s])) for s in x["fits"])
                dphi = max(dphi, dp)
                q = {"rep": x["rep"], "mode": x["mode"], "max_abs_dphi": dp}
                if set(x["fits"]) == {"base", "later"}:
                    d = x["fits"]["later"]["phi"][0] - x["fits"]["base"]["phi"][0]
                    q["abs_dD"] = abs(d - r["D_hat"])
                    dD = max(dD, q["abs_dD"])
                per.append(q)
            # D from the two single-period processes of the same replicate
            for j in sorted({x["rep"] for x in do}):
                m = {x["mode"]: x for x in do if x["rep"] == j}
                if "base" in m and "later" in m and j in zs:
                    d = m["later"]["fits"]["later"]["phi"][0] - m["base"]["fits"]["base"]["phi"][0]
                    per.append({"rep": j, "mode": "separate processes", "abs_dD": abs(d - zs[j]["D_hat"])})
                    dD = max(dD, abs(d - zs[j]["D_hat"]))
            out["zero_change_fit_order"] = {"n_rows": len(do), "reps": sorted({x["rep"] for x in do}),
                                            "max_abs_dphi": dphi, "max_abs_dD": dD, "per": per}
    for fp in sorted((OUT / "drift_mc_runs").glob("kf*.jsonl")):
        R = list({(r["estimator"], r["rep"]): r for r in reversed(_rows(fp))}.values())   # one row per replicate (first kept)
        for e in EST:
            Re = [r for r in R if r["estimator"] == e]
            if Re:
                k = sum(r["alarm"] for r in Re)
                out.setdefault("drift_mc", []).append({
                    "file": fp.name, "kf_factor": Re[0]["f"], "estimator": e, "n": len(Re), "false_alarms": k, "rate": k / len(Re),
                    "rate_ci95": cp_interval(k, len(Re)), "D_hat_mean_pct": float(np.mean([math.exp(r["D_hat"]) - 1 for r in Re]) * 100),
                    "D_hat_sd_pct": float(np.std([r["D_hat"] for r in Re], ddof=1) * 100) if len(Re) > 1 else None,
                    "se_median_pct": float(np.median([r["se"] for r in Re]) * 100),
                    "all_converged": all(r["converged"] for r in Re)})
    diag = []
    sets = {}
    for sd in (42, 123):
        hl = _rows(RESULTS_DIR / "p2" / "headline_mw_runs" / f"snr40_seed{sd}.jsonl")
        sets[("base", 40.0, sd)] = [dict(r, j=r["seed_key"][2]) for r in hl if r["seed_key"][2] < 10]
    for fp in sorted((OUT / "bias_diag_runs").glob("*.jsonl")):
        R = _rows(fp)
        if R:
            sets[(R[0]["variant"], float(R[0]["snr_db"]), R[0].get("seed", 42))] = R
    for (v, snr, sd), R in sorted(sets.items(), key=lambda kv: (kv[0][2], kv[0][0], kv[0][1])):
        e = np.array([r["err_log"][0] for r in R])
        c = np.array([r["crb_log"][0] for r in R])
        se = np.array([r["se_log"][0] for r in R])
        k = int(np.sum(np.abs(e) <= 1.645 * se))
        diag.append({"seed": sd, "variant": v, "snr_db": snr, "n": len(R), "bias_pct": float(np.mean(np.exp(e) - 1) * 100),
                     "bias_se_pct": float(np.std(np.exp(e) - 1, ddof=1) / math.sqrt(len(R)) * 100),
                     "rmse_pct": float(np.sqrt(np.mean(e**2)) * 100), "crb_pct": float(np.sqrt(np.mean(c**2)) * 100),
                     "rmse_over_crb": float(np.sqrt(np.mean(e**2)) / np.sqrt(np.mean(c**2))),
                     "coverage90_wald": k / len(R), "cB_bias_pct": float(np.mean([math.exp(r["err_log"][1]) - 1 for r in R]) * 100),
                     "datasets": sorted(r["j"] for r in R)})
    out["bias_diag"] = diag
    fr = [x for x in out.get("drift_mc", []) if x.get("file", "").endswith("_freight.jsonl")]
    if fr:                                # drift Monte Carlo at the frozen configuration, on its own
        save_result("p3/drift_mc_freight", {"drift_mc": fr}, cfg={"true_change": 0, "N_per_period": 50, "snr_db": 40,
                                                                  "rows": "results/p3/drift_mc_runs/kf0.8_freight.jsonl"}, seed=45)
    save_result("p3/validation_mc", out, cfg={
        "kappa": {"N_per_period": 50, "estimator": "coest (kB0, cB, kf, kH0)", "kappa": KAPPA_COEST, "ranges": RANGES,
                  "kf_sampling": "stratified log-normal sigma 0.35", "x": "U(2%, 10%) decrease"},
        "drift": {"true_change": 0, "N_per_period": 50, "snr_db": 40},
        "bias": {"datasets": "keys (42, 40, j), 4-wheel headline; same data at each SNR", "refined": "0.25 Hz table, exact sub-band scoring"}},
        seed=45)
    print(json.dumps(out, indent=1, default=str)[:4000])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--kappa", action="store_true")
    ap.add_argument("--zero", action="store_true", help="--kappa: zero-change study (true change 0, same draws and seeds)")
    ap.add_argument("--drift", action="store_true")
    ap.add_argument("--bias", action="store_true")
    ap.add_argument("--summarise", action="store_true")
    ap.add_argument("--kappa-sing-se", action="store_true", help="sensitivity SE (c_B fixed) for the singular kappa replicates")
    ap.add_argument("--reps", type=int, nargs="+", default=None, help="--kappa-sing-se on these replicates (check file)")
    ap.add_argument("--kappa-diag", type=int, default=None, help="likelihood diagnostic for one kappa replicate (rep number)")
    ap.add_argument("--kappa-diag-cb", action="store_true", help="restart diagnostic for the kappa replicates with c_B at its bound (--reps to select)")
    ap.add_argument("--diag-order", type=int, default=None, help="fit-order diagnostic for this zero-change replicate")
    ap.add_argument("--order-mode", choices=("base", "later", "reversed"), default="base",
                    help="--diag-order: one period alone in this process, or both in reversed order")
    ap.add_argument("--kappa-two-start", action="store_true", help="two-start sensitivity on all kappa replicates (--reps to select)")
    ap.add_argument("--j0", type=int, default=0)
    ap.add_argument("--j1", type=int, default=1)
    ap.add_argument("--f", type=float, default=0.8)
    ap.add_argument("--tag", default="", help="run-file suffix, e.g. _freight for the current configuration")
    ap.add_argument("--snr", type=float, default=60.0)
    ap.add_argument("--band", choices=("empty", "laden"), default=None, help="--kappa within a payload band")
    ap.add_argument("--refined", action="store_true")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--kb", type=int, default=None, help="debiasing kernel half-width in bins")
    ap.add_argument("--ksub", type=int, default=None, help="estimator roughness sub-bands per third octave (data: 16)")
    ap.add_argument("--smooth", type=float, default=None, help="random-walk prior step sigma on log sub-band levels (dB)")
    a = ap.parse_args()
    if a.kappa:
        BAND[0] = a.band
        kappa(a.j0, a.j1, a.tag, zero=a.zero)
    if a.kappa_sing_se:
        BAND[0] = a.band
        kappa_sing_se(a.tag, a.reps)
    if a.kappa_diag is not None:
        BAND[0] = a.band
        kappa_diag(a.kappa_diag, a.tag)
    if a.kappa_diag_cb:
        BAND[0] = a.band
        kappa_diag_cb(a.tag, a.reps)
    if a.kappa_two_start:
        BAND[0] = a.band
        kappa_two_start(a.tag, a.reps)
    if a.diag_order is not None:
        BAND[0] = a.band
        kappa_diag_order(a.diag_order, a.order_mode, a.tag)
    if a.drift:
        drift(a.j0, a.j1, a.f, a.tag)
    if a.bias:
        bias(a.j0, a.j1, a.snr, a.refined, a.seed, a.kb, a.ksub, a.smooth)
    if a.summarise:
        summarise()
