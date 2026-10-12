# Table 1. Model parameters and sources

| Group | Parameter | Value | Unit | Source |
|---|---|---|---|---|
| Material | E | 2.10e11 | Pa | doc §16 (standard steel) |
| Material | nu | 0.3 | - | doc §16 |
| Material | rho | 7850 | kg/m^3 | doc §16 |
| Axle | length | 2.18 | m | placeholder: typical standard-gauge freight axle |
| Axle | sections [outer ξ, d] | [[0.64,0.175],[0.86,0.2],[0.9,0.16],[1.09,0.13]] | m | placeholder: body / wheel seat / dust-guard collar / journal, typical EN 13103-type proportions |
| Axle | wheel_xi | 0.75 | m | placeholder: contact plane ~ half of 1.5 m contact-point spacing |
| Axle | journal_xi | 0.995 | m | placeholder: mid-journal bearing centre |
| Axle | n_elements | 32 | - | brief: 20-40 elements; convergence checked at 20/30/40 |
| Axle | damping_zeta | 0.01 | - | placeholder: 1% stiffness-proportional at f_ref |
| Axle | damping_fref | 80 | Hz | placeholder: typical first wheelset bending frequency |
| Wheel | mass | 350 | kg | placeholder: 920 mm freight wheel |
| Wheel | diametral_inertia | 20 | kg m^2 | placeholder: disc estimate m r^2/4 with rim correction |
| Wheel | r0 | 0.4575 | m | doc §13 (new 915 mm wheel) |
| Bearing | kB0 | 1.0e9 | N/m | placeholder: tapered roller unit radial stiffness, order 1e8-1e9 |
| Bearing | cB | 5.0e3 | N s/m | placeholder: EHL/structural damping |
| Bearing | load_exponent | 0.1 | - | doc Eq. (12): Q ~ delta^(10/9) gives k ~ Q^(1/10) |
| Axlebox | mass | 60 | kg | placeholder: housing + outer ring + adapter |
| Primary | kp | 1.0e6 | N/m | placeholder: freight primary vertical stiffness per axlebox |
| Primary | cp | 1.0e4 | N s/m | placeholder: equivalent linear damping per axlebox |
| Payload | W_min | 5.5 | t | placeholder: empty freight wagon axle load |
| Payload | W_max | 22.5 | t | placeholder: loaded (22.5 t axle load class) |
| Payload | W0 | 22.5 | t | reference load for kB0 (loaded) |
| Rail BS113A | A | 0.00717 | m^2 | CT23 Table 1 |
| Rail BS113A | rho | 7850 | kg/m^3 | CT23 Table 1 |
| Rail BS113A | E | 207.0e9 | Pa | CT23 Table 1 |
| Rail BS113A | I | 2.35e-05 | m^4 | CT23 Table 1 |
| Rail BS113A | G | 81.0e9 | Pa | CT23 Table 1 |
| Rail BS113A | kappa | 0.34 | - | CT23 Table 1 |
| Rail 60E1 | A | 0.00767 | m^2 | verify: EN 13674-1 60E1 section area 76.70 cm^2 (quoted from memory) |
| Rail 60E1 | I | 3.038e-05 | m^4 | verify: EN 13674-1 60E1 vertical-bending I_x 3038.3 cm^4 (quoted from memory) |
| Foundation | standard_kf_lab | 154.0e6 | N/m^2 | CT23 Sec. 5.1.1: ~100 MN/m per fastener (lab, Thompson et al.) at 0.65 m spacing |
| Foundation | resilient_kf | 7.7e6 | N/m^2 | CT23 Sec. 5.1.1 (pass-by rail deflection, Cox & Wang) |
| Foundation | eta_f | 0.2 | - | CT23 Table 1 / Sec. 5.1.1 (literature range 0.2-0.3) |
| Contact | C_H | 89.0e9 | N/m^1.5 | CT23 Sec. 5.1.2 citing Sanchis et al. (metro wheel/rail radii; freight wheel and 60E1 head radii differ: verify) |
| Layout | positions | [0.0,2.05,6.52,8.57,16.62,18.67,23.14,25.19,33.24,35.29,39.76,41.81] | m | CT23 Sec. 5.1.3 / Fig. 5: axle spacing 2.05, bogie centres 10.10 within a car, 6.52 across a coupling (positions derived from these) |


15 of 35 entries are placeholders. Vehicle masses (wheel, axlebox, unsprung) stay placeholders until the target vehicle is confirmed; values marked 'verify' are to be checked against the cited standard.

Source: `config/params.yaml`, `config/track.yaml`
