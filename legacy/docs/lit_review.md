# Phase 0 literature check (P0.2)

Date: 2026-10-11. Search tool: web search only. Crossref, ScienceDirect and arXiv
direct access are blocked by this environment's network policy. A DOI is listed as
**verified** only when a publisher or institutional-repository record surfaced it in
a search result; otherwise it is marked *DOI not verified* and must be checked
before citing. Several full texts could not be opened, so claims about their
contents rest on abstracts and repository summaries.

## 1. H1: gPC degree near resonance and the group Π = σ_ω/(ζ ω_n)

### What is already established

| Ref | What it shows | DOI |
|---|---|---|
| Jacquelin, Adhikari, Sinou, Friswell, *J. Sound Vib.* 356 (2015) 144–154, "Polynomial chaos expansion in structural dynamics: accelerating the convergence of the first two statistical moment sequences" | PC of FRFs of lightly damped systems converges very poorly near the deterministic resonances. About 200 polynomials are needed there; Aitken-type acceleration of the moment sequences cuts this to < 50. | 10.1016/j.jsv.2015.06.039 (verified) |
| Jacquelin, Adhikari, Sinou, Friswell, *J. Eng. Mech.* 141(4) (2015) 04014145, "Polynomial chaos expansion and steady-state response of a class of random dynamical systems" | PCE may be unsuitable for the steady-state response near a deterministic eigenfrequency. The required order can be very high, especially at low damping. | 10.1061/(ASCE)EM.1943-7889.0000856 (verified) |
| Jacquelin, Adhikari, Friswell, Sinou, *J. Eng. Mech.* 142(8) (2016), "Role of roots of orthogonal polynomials in the dynamic response of stochastic systems" | The eigenfrequencies of the PC-extended system are tied to the roots of the basis polynomials. Legendre keeps them in a bounded interval; Hermite spreads them, so smoothing becomes less effective as the order grows. | 10.1061/(ASCE)EM.1943-7889.0001102 (verified) |
| Pagnacco, Sarrouy, Sampaio, Souza de Cursi (2017), "Pitfalls in the frequency response represented onto polynomial chaos for random SDOF mechanical systems" (HAL hal-01590996) | Near resonance, standard bases struggle and the response PDF can be multimodal. | *DOI not verified* |
| Sarrouy, Pagnacco, Souza de Cursi, *Mech. Ind.* 17 (2016) 206, "A constant phase approach for the frequency response of stochastic linear oscillators" | Reformulation to cure the near-resonance difficulty. | 10.1051/meca/2015057 (verified) |
| Yaghoubi, Marelli, Sudret, Abrahamsson, *Prob. Eng. Mech.* 48 (2017) 39–58 | Frequency shifts from parameter uncertainty force very high-order PCEs even for 1–2 DOF FRFs. Proposes a stochastic frequency transformation. | 10.1016/j.probengmech.2017.04.003 (verified) |
| Kara, Ferguson, *J. Sound Vib.* 566 (2023) 117930 | The PCE order must be very high for FRF moments at resonance in lightly damped structures. Proposes a two-stage PCE for bounds. | 10.1016/j.jsv.2023.117930 (verified) |
| Adhikari, Pascual, *Prob. Eng. Mech.* 44 (2016) 2–17, "The 'damping effect' in the dynamic response of stochastic oscillators" | A random natural frequency acts as extra effective damping in the *mean* response. Closed-form equivalent damping for a uniform ω_n. | 10.1016/j.probengmech.2015.09.017 (verified) |
| (2026) *Prob. Eng. Mech.*, "Equivalent damping and closed-form response statistics of stochastic oscillators" (ScienceDirect pii S0266892026001268) | Closed-form mean, equivalent damping and frequency-dependent variance of a damped SDOF with uncertain ω_n, valid at resonance. | *authors and DOI not retrieved* |
| Wan, Karniadakis, *CMAME* 195 (2006) 5582–5596, "Long-term behavior of polynomial chaos in stochastic flow simulations" | Fixed-degree gPC degrades over long integration times; multi-element gPC fixes it. | *DOI not verified* |
| Pettit, Beran, *J. Sound Vib.* 294(4–5) (2006) 752–779, "Spectral and multiresolution Wiener expansions of oscillatory stochastic processes" | For a sinusoid with random frequency, the Wiener–Hermite expansion loses energy after a few periods. This is the time-domain form of the σ_ω·t growth. Wiener–Haar removes the loss. | *DOI not verified* |
| Le Maître, Mathelin, Knio, Hoteit, *Discrete Contin. Dyn. Syst.* 28(1) (2010) 199–226, "Asynchronous time integration for polynomial chaos expansion of uncertain periodic dynamics" | Rescaled time keeps the spectrum narrow for uncertain limit cycles. | *DOI not verified* |
| Manohar & Keane (1990s; via Adhikari's citation) | The statistical overlap factor (std of natural frequency ÷ mean spacing) governs response variability. Π is the same idea normalised by the half-power bandwidth instead of the mode spacing. | *original not retrieved* |

### Assessment

- **The phenomenon is known.** High PC order near resonance, getting worse as damping drops and worse for Hermite than Legendre, is established. The Jacquelin 2015/2016 papers and Yaghoubi 2017 are the core citations.
- **No source I could reach states a quantitative degree law.** Specifically, none gives p_req ∝ Π (bounded/Legendre) or p_req ∝ Π² (Gaussian/Hermite) with Π = σ_ω/(ζ ω_n).
  - I could not read the full texts of the 2016 *J. Eng. Mech.* note or the 2026 *Prob. Eng. Mech.* paper, and either could contain it.
  - **Before claiming the scaling law as new, someone with library access must check those two.**
- **Recommended framing:** a quantified, pre-training diagnostic that extends Jacquelin et al. and Adhikari & Pascual. It is not a new failure mechanism.
- **Our P0.3 result (`results/p0/h1_sdof*.json`) corrects the H1 statement in the brief.** For uniform (Legendre) inputs the required degree grows like Π (p ≈ 4Π at 1% variance error), not Π². Π² holds only asymptotically for log-normal (Hermite) inputs, with p ≈ 5.6Π².
  - This matches the root-spreading explanation in Jacquelin et al. (2016).
  - It matches the approximation-theory argument: Bernstein ellipse for Legendre against a strip of analyticity for Hermite.

## 2. Overall method: stop rule check

Stop rule (from the brief): stop if a stochastic or separable PINN identifying
bearing or support parameters in rotating machinery or a railway wheelset is already
published.

| Ref | Relation | DOI |
|---|---|---|
| Li & Onwunta (2026), S²-PINN, arXiv:2610.03303 (NeurIPS 2026) | Generic stochastic separable PINN with a 2-scalar inverse on manufactured PDEs. No machinery application. | arXiv |
| Zhang, Lu, Guo, Karniadakis, *J. Comput. Phys.* (2019), "Quantifying total uncertainty in physics-informed neural networks for solving forward and inverse stochastic problems" | aPC + PINN for forward and inverse stochastic problems (generic). | *DOI not verified* (arXiv:1809.08327) |
| Sharma, Novák, Shields (2024), "Physics-constrained polynomial chaos expansion for scientific machine learning and uncertainty quantification" (PC²) | Physics-constrained PCE; S²-PINN's external baseline. | *journal DOI not verified* (arXiv:2402.15115) |
| (2026) arXiv:2609.23077, "PINN surrogates with polynomial chaos-based uncertainty propagation for stochastic MPC" | PINN + PCE, control application. | arXiv |
| Parziale, Lomazzi, Giglio, Cadini, *Sensors* 24(1) (2024) 207 | **Deterministic** PINN estimating 5 health parameters (support stiffnesses, damping) of an extended Jeffcott rotor from disk displacement. Closest machinery match, but no UQ structure and no separability. | 10.3390/s24010207 (verified) |
| AMB bearing parameter identification by Bayesian inference with gPC (*J. Braz. Soc. Mech. Sci. Eng.*, 2021) | gPC surrogate + Bayesian ID of bearing parameters. Not a PINN. | 10.1007/s40430-021-03287-9 (from publisher URL) |
| PD-SOVNet, arXiv:2604.06620 | Physics-driven operator network: wheel polygon roughness from axle-box vibration. A different target, and not stochastic. | arXiv |
| Stochastic harmonic balance + PCE (rotordynamics with clearance: HAL hal-02556332, hal-03258030; LCO: QUB; Fourier-gPC, *JSV* 2024) | Classical frequency-domain PCE. **Must be cited for the fixed harmonic time basis** (risk R11). | various |
| "How to avoid trivial solutions in PINNs", arXiv:2112.05620 | PINNs on oscillators collapse onto x = 0. Matches what we saw for forced MLP PINNs in P0.4. | arXiv |

**Verdict:** no paper found that does stochastic or separable PINN identification of
bearing or support parameters in rotating machinery or a railway wheelset. **The stop
rule is not triggered.** Caveat: web search only, without Scholar/Scopus. The nearest
work is Parziale et al. (2024, deterministic PINN, Jeffcott rotor) and gPC-Bayesian
bearing identification (no PINN).
