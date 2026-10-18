# Literature check: joint rail-roughness / bearing-support-stiffness identification from ABA

Date: 2026-10-11. Scope: prior art for identifying the wheelset bearing-support stiffness
k_B0 (axlebox support resonance, roughly 500–650 Hz) from in-service axle-box acceleration
(ABA) over many passes. The method uses a Whittle likelihood, per-band roughness levels as
nuisance parameters, speed diversity across passes, and payload known from WIM.

## How this was searched, and how far to trust it

- **Only the web-search tool worked.** WebFetch failed with DNS errors for every host tried (research.chalmers.se, mdpi, doaj, ruja.ujaen.es, repository.cam.ac.uk, api.semanticscholar.org). `curl` through the agent proxy got 403 for every academic host tried: chalmers, mdpi, tandfonline, springer, TU Delft, DiVA, polimi, HAL, Scholar, ResearchGate, doi.org, OpenAlex, EuropePMC and dblp.
- **No full text was opened.** Every claim below comes from search-result snippets: abstracts, repository records and highlights.
- **DOI labels:**
  - "(seen)": the DOI appeared in a search result.
  - "(inferred)": built from a ScienceDirect pii or URL, not shown as a DOI.
  - "not seen": no DOI surfaced.
- **Unverified** marks any item where the authors, venue or content could not be confirmed from a snippet.
- **Coverage gap:** Chinese- and Japanese-language literature was not searched. Much axle-box bearing dynamics work is published in Chinese journals, so this is a real blind spot for section C.

---

## A. Indirect rail-roughness estimation from ABA with a known or modelled transfer function

| Ref | What it does (from abstract/snippet) | DOI |
|---|---|---|
| **Pieringer, A., Kropp, W. (2022)**, "Model-based estimation of rail roughness from axle box acceleration", *Applied Acoustics* 193, 108760 (Chalmers) | Time-domain method. (1) An LMS source-identification step recovers the contact force from ABA. (2) Combined roughness comes from a nonlinear Hertzian contact model. (3) Wheel and rail roughness are separated by cycle-averaging over the wheel perimeter. In simulation, 1/3-octave error is < 1 dB *when track dynamics are known*. Rail-pad stiffness is the most critical parameter: a 20 % error gives up to 3.5 dB in single bands. **The authors state the method must be extended to extract track parameters and roughness simultaneously.** | 10.1016/j.apacoust.2022.108760 (seen) |
| **Carrigan, T.D., Talbot, J.P.**, "Extracting Information from Axle-Box Acceleration: On the Derivation of Rail Roughness Spectra in the Presence of Wheel Roughness", *Notes on Numerical Fluid Mechanics and Multidisciplinary Design* vol. 150 (Springer), c. 2021 | A calibrated roughness-to-ABA transfer function suffers when track dynamics vary and when wheel roughness is present. The proposal: extract the track's dynamic stiffness parameters from the ABA itself, giving a section-wise transfer function, and remove wheel roughness by synchronous averaging. | chapter URL 10.1007/978-3-030-70289-2_29 (seen in URL) |
| **Carrigan, Talbot (and Fidler, per the dataset record)**, "On the derivation of rail roughness spectra from axle-box vibration: development of a new technique" | "Progress towards a new stochastic frequency-domain inverse method" for wavelength spectra of roughness from ABA. It is meant to compensate for vehicle speed and track dynamics, and is demonstrated on time-domain simulations. | venue/year **unverified** (Emerald OA edited volume; Cambridge dataset record) |
| **Faccini, L., Karaki, J., Di Gialleonardo, E., Somaschini, C., Bocciolone, M., Collina, A. (2023)**, "A Methodology for Continuous Monitoring of Rail Corrugation on Subway Lines Based on Axlebox Acceleration Measurements", *Applied Sciences* 13(6), 3773 | Infers rail irregularity from ABA through a frequency-domain vertical wheel–rail model. Compares a state-of-the-art method with a new one. Uses the trend of irregularity power to flag where grinding is needed. | 10.3390/app13063773 (seen) |
| Karaki et al. (2022), Politecnico di Milano | Roughness profile estimated from ABA on an in-service metro vehicle. Some peak-to-peak differences against direct measurement remain. | not seen; **partially verified** |
| Lanzillo (2023), MSc thesis, Politecnico di Milano | Transfer functions from three wheel–rail models of increasing complexity, applied to a Milan metro train. Changes in measurement-system parameters and in **speed** cause a large dispersion of the results, especially near wheel–rail resonances. | thesis |
| **Yu, X., Muñoz-Moreno, S., Urda, P., Fernández-Aceituno, J., Rodríguez-Gómez, M., Escalona, J.L. (2025)**, "Experimental study of the use of a transfer function to find rail corrugation from axle-box accelerations", *Measurement* 249, 117058 | Scale-track study comparing a kinematic TF with a 2-DOF vehicle–track TF. The kinematic TF gives reasonable but not accurate estimates at moderate speed. The 2-DOF model cannot explain some peaks that are not excitation frequencies. The authors propose normalising acceleration by V² to reduce speed dependence. | 10.1016/j.measurement.2025.117058 (seen) |
| **Stoura, C.D., Dertimanis, V.K., Hoelzl, C., Kossmann, C., Cigada, A., Chatzi, E.N. (2023)**, "A Model-Based Bayesian Inference Approach for On-Board Monitoring of Rail Roughness Profiles: Application on Field Measurement Data of the Swiss Federal Railways Network", *Structural Control and Health Monitoring* | Reduced-order vehicle model with Bayesian joint input–state estimation, where the input is the roughness profile. **Selected vehicle-model parameters are updated with an unscented Kalman filter using diagnostic-vehicle measurements.** Applied to SBB data. | 10.1155/2023/8855542 (seen) |
| Stoura, Dertimanis, Chatzi (2023), "Rail Roughness Identification Via On-Board Acceleration Data and Bayesian Filtering", SHM 2023 proceedings | Conference version of the above: sequential Bayesian input estimation, flags welds and squats. | 10.12783/shm2023/37071 (seen) |
| Dertimanis, V.K., Zimmermann, M., Corman, F., et al. (2020), "On-board monitoring of rail roughness via axle box accelerations of revenue trains with uncertain dynamics", IMAC-XXXVII, *Model Validation and Uncertainty Quantification* Vol. 3, pp. 167–171 | Dual Kalman filter for joint input/state estimation with a reduced train model, under uncertain train dynamics. In simulation, stiffness varies with a random temperature field. | not seen |
| "Calibration of transfer functions on a standstill vehicle for on-board indirect measurements of rail acoustic roughness", HAL hal-03233638 (French MEEQUAI project) | Calibrates and validates the transfer functions for indirect acoustic-roughness measurement using standstill-vehicle measurements together with numerical simulation. | authors **unverified** |
| Salvador Zuriaga, P., Naranjo Ornedo, J.M., Insa Franco, R., Teixeira, P.F. (2016), "Axlebox accelerations: Their acquisition and time-frequency characterisation for railway track monitoring purposes", *Measurement* | Valencia metro: optimal sampling, filtering and sensor location for ABA; time–frequency analysis detects a wide set of defects. | 10.1016/j.measurement.2016.01.012 (seen) |
| Tanaka, H., Matsumoto, M., Harada, Y. (2016), "Application of axle-box acceleration to track condition monitoring for rail corrugation management", 7th IET Conf. Railway Condition Monitoring | Compares inspection-car ABA with ground-measured roughness in Japan. Corrugation can be managed from leading-axle ABA at usual speed. | 10.1049/cp.2016.1191 (seen in URL) |
| Molodova, M., Li, Z., Núñez, A., Dollevoet, R. (2014), "Automatic Detection of Squats in Railway Infrastructure", IEEE journal (T-ITS **unverified**) | Automatic squat detection from ABA on trains, building on the group's simulation, prototype and field-testing work. | not seen |
| Li, Z., Molodova, M., Núñez, A., Dollevoet, R. (2015), "Improvements in Axle Box Acceleration Measurements for the Detection of Light Squats in Railway Infrastructure", IEEE Transactions (journal **unverified**) | Uses longitudinal ABA to raise sensitivity to light squats. | not seen |
| Wang, Q., Zhao, H., Gong, D., Zhou, J., Xiao, Z. (2024), "Quantitative Detection of Vertical Track Irregularities under Non-Stationary Conditions with Variable Vehicle Speed", *Sensors* 24(12), 3804 | Order tracking resamples ABA by wheel rotation to handle variable speed. A simplified wheel–rail model plus double integration gives irregularity. | 10.3390/s24123804 (seen) |
| "Theoretical investigation into the measurability of rail unevenness and corrugation using the dynamic response of axle box and bogie", *Proc. IMechE Part F* (2020) | Frequency-domain analysis with multiple wheel–rail contacts. Axle-box response is shaped by P2 resonances (low and mid frequency) and rail standing waves (higher frequency). Unevenness measurement is mainly limited by P2. | 10.1177/0954409720923213 (seen); authors **unverified** |
| "Evaluating Rail Surface Roughness from Axle-Box Acceleration Measurements: Computational Metrology Approach", *J. Transp. Eng. Part A* 147(12) (2021) | Computational-metrology method for roughness from vertical ABA (Canadian passenger car). Useful for wavelengths of roughly 3–25 m. | 10.1061/JTEPBS.0000601 (seen); authors **unverified** |
| Lee, J.-S. et al. (2010), KSR conference (Korea Railroad Research Institute) | Rail irregularity from ABA on in-service high-speed trains using a Kalman filter plus a frequency-selective filter, checked against a laser system. | not seen |
| EN 15610:2019 | Direct method only. **Clause 1.3 explicitly excludes indirect methods.** There is therefore no standard indirect ABA method in EN 15610. | standard |

**Searched for but not found:**
- The suggested Carlberger/Torstensson/Nielsen/Frid "iterative methodology" paper. The Chalmers ABA roughness paper that surfaced is Pieringer & Kropp.
- A De Rosa (Politecnico di Milano) ABA roughness paper. Only Leonardi, Alfi, Bruni (2016) on Kalman-filter track geometry surfaced.
- Kraft's indirect method.
- Jeong (KTX).
- Hirose/Ohmori.
- An LSTM-based ABA roughness inversion by Ma, Zhang or Wang.

All of these are **unverified / not found**, which is not the same as nonexistent.

---

## B. Joint or blind estimation of roughness and the transfer function or system parameters; speed diversity

### B1. Railway: track stiffness from ABA, with or without joint roughness

| Ref | What it does | Joint roughness? | Speed diversity used for identifiability? |
|---|---|---|---|
| **Carrigan, T.D., Talbot, J.P. (2023)**, "A new method to derive rail roughness from axle-box vibration accounting for track stiffness variations and wheel-to-wheel coupling", *Mech. Syst. Signal Process.* 192, 110232 | Fits a model transfer function to the **P2 peak** of the ABA spectrum to estimate track stiffness, updated continuously along the track. Accounts for multiple wheels on one rail and removes wheel roughness with a comb filter. Validated by simulation and Victoria line trials. One snippet notes the measured frequency response is independent of vehicle speed except in some track sections. | **Yes**: track stiffness plus roughness spectrum, sequentially (stiffness first, then deconvolution) | Not as an identifiability mechanism, from what was seen |
| Cambridge (Carrigan & Talbot), *Lecture Notes in Mechanical Engineering* (ISBN 978-981-99-7851-9), repository 1810/375902 | Frequency-domain method with several flexible wheelsets on two rails. Track stiffness is updated from the P2 peak; comb filter for wheel roughness. On London Underground data, spectra fall within 10 dB of direct measurement over most of 40–1000 mm. | Yes (same scheme) | Not seen |
| ISMA 2022 proceedings, Contribution 434, "Monitoring rail roughness using axle-box accelerometers …" | Fits the FRF of a rigid-wheel model to the square root of the measured ABA PSD around P2, section by section (62 m sections). Stiffness lands within 18 % of nominal. | Yes | Not seen; authors **unverified** (very likely the Cambridge group) |
| **Shen, C., Zhang, P., Dollevoet, R., Zoeteman, A., Li, Z. (2023)**, "Evaluating railway track stiffness using axle box accelerations: A digital twin approach", *MSSP* 204, 110730 | Digital twin: a Gaussian-process library of simulated ABA features from a vehicle–track model, used to estimate **rail-pad and ballast stiffness and the track-irregularity level** from ABA. Frequency bands include 400–700 Hz. **No vehicle-side parameters** are identified. (Detail added 2026-10-15 from the user's reading of the full text.) | Irregularity enters as **a single level parameter** estimated with the stiffnesses | **No**: three speeds are **estimated separately**, not pooled |
| **Hoelzl, C.A., Dertimanis, V., Ancu, L., Kollros, A., Chatzi, E. (2022)**, "Vold-Kalman Filter Order tracking of Axle Box Accelerations for Railway Stiffness Assessment", arXiv:2209.12899 | Vold-Kalman order tracking splits ABA into periodic wheel-related and track-related (sleeper-passing) components. Links track stiffness to sleeper-passage amplitude. Notes that common methods are not conditioned on speed. | No | Uses speed to track orders, not to separate roughness from the TF |
| **Quirke, P., Cantero, D., OBrien, E.J., Bowe, C. (2017)**, "Drive-by detection of railway track stiffness variation using in-service vehicles", *Proc. IMechE F* 231(4), 498–514 | Cross-entropy optimisation finds the track-stiffness profile whose simulated bogie response best matches measured acceleration. Numerical, 2-D half-bogie. | Roughness handling **unverified** | No |
| Malekjafarian, A., OBrien, E.J., Quirke, P., Cantero, D., Golpayegani, F. (2021), "Railway Track Loss-of-Stiffness Detection Using Bogie Filtered Displacement Data Measured on a Passing Train", *Infrastructures* 6, 93 | Title only retrieved | **unverified** | **unverified** |
| "Axle Box Accelerometer Signal Identification and Modelling", ch. in *Model Validation and Uncertainty Quantification* Vol. 3 (IMAC) | **Output-only LPV-AR model of ABA with vehicle speed as the scheduling variable** (SBB diagnostic vehicle). Speed, rail condition and track type drive the response; the sleeper-passing frequency is captured. | No (black-box) | Speed enters as a scheduling variable, not as a roughness/TF separation device; authors **unverified** |
| "Simultaneous identification of the frequencies and track irregularities of high-speed railway bridges from vehicle vibration data", *MSSP* (2020/21), pii S0888327020307986 | Kalman filter jointly estimates **bridge** frequencies and track irregularity from vehicle vibration (simulation). | Yes (bridge frequencies, not vehicle parameters) | No; authors **unverified** |

### B2. Road vehicles and drive-by bridge monitoring: close analogues of using speed or several passes to remove roughness

| Ref | What it does |
|---|---|
| **Jin, N., Yang, Y.B., Dimitrakopoulos, E.G., Paraskeva, T.S., Katafygiotis, L.S.**, "Application of short-time stochastic subspace identification to estimate bridge frequencies from a traversing vehicle", *Engineering Structures* 230 (2021), 111688 | **Removes road roughness using a "transformed residual" response from two traverses of the vehicle at different speeds.** Identifies the first two bridge frequencies at 10–20 m/s even with high roughness. Numerical (sprung mass and MDOF vehicle). DOI likely 10.1016/j.engstruct.2020.111688 (inferred from the article number). |
| *Developments in the Built Environment* vol. 14 (2023), PSD-based drive-by damage algorithm | **Removes road irregularity by subtracting responses at different speeds in the spatial domain**, then uses a PSD damage database. Quarter-car on a 15 m beam, 1800 crack scenarios. Authors **unverified**. |
| Taylor & Francis chapter "Mitigation of unwanted effects in drive-by acceleration data for bridge monitoring" (10.1201/9781003483755-191) | Subtracts the responses at two speeds in the spatial domain to isolate the bridge component of the PSD. Authors **unverified** (URL slug suggests Casero, González, Feng). |
| **Keenahan, J., Ren, Y., OBrien, E.J. (2019)**, "Determination of Road Profile Using Multiple Passing Vehicle Measurements" (UCD) | Inverse integration plus cross-entropy optimisation. **Data from several vehicles give the profile without prior knowledge of vehicle properties**, but only *relative* vehicle properties are obtained. A later UCD thesis adds MCMC Bayesian updating. |
| Ren, Y., Feng, K., OBrien, E., Li, W., He, H., "Bridge Profile and Vehicle Property Determination Using Vehicle Fleet Monitoring Concept", *Int. J. Struct. Stab. Dyn.* | Fleet of vehicles; inverse Newmark-β plus cross-entropy gives the bridge profile and vehicle properties. Year and DOI not seen. |
| **Liu, L., Guo, X., Yang, X., Liu, L. (2024)**, "Combined Identification of Vehicle Parameters and Road Surface Roughness Using Vehicle Responses", *Applied Sciences* 14(22), 10310 | 4-DOF half-car with an EKF for unknown inputs. Vehicle parameters and axle forces are identified first. Tire stiffness comes next, using the fixed time lag between front and rear axles over the same roughness. Roughness is estimated last. States that unknown parameters coupled with unknown roughness force mutual iteration in existing methods. 10.3390/app142210310 (seen). |
| Yang, Y.B., Lin, C.W., Yau, J.D. (2004), "Extracting bridge frequencies from the dynamic response of a passing vehicle", *J. Sound Vib.* 272, 471–493 | Origin of drive-by bridge frequency extraction. 10.1016/S0022-460X(03)00378-X (seen). |
| Yang, Y.B., Zhang, B., Qian, Y., Wu, Y. (2018), "Contact-Point Response for Modal Identification of Bridges by a Moving Test Vehicle", *IJSSD* | Contact-point response removes the vehicle's own frequencies. Residual contact responses from two axles or vehicles then cancel roughness. |
| Malekjafarian, A., McGetrick, P., OBrien, E.J. (2015), "A Review of Indirect Bridge Monitoring Using Passing Vehicles", *Shock and Vibration* 286139 | Review. 10.1155/2015/286139 (seen). |

**Mechanism note for the paper.** The drive-by literature already uses the idea that roughness is fixed in wavenumber while the structural resonance is fixed in frequency, through multi-speed or multi-pass subtraction. It does so for *bridge* frequencies seen through a road vehicle, by **subtraction or residuals**, not by a likelihood with per-band roughness nuisance parameters. That literature has to be cited as the conceptual antecedent of the speed-diversity idea.

---

### B3. Railway-vehicle suspension identification (added 2026-10-15)

| Ref | What it does | Relation to this work |
|---|---|---|
| **Lebel, D., Soize, C., et al. (2019)**, *J. Sound Vib.* (title, volume and pages to be filled) | Railway-vehicle suspension parameter identification as a statistical inverse problem | Suspension parameters, below the axle-box support band; how track irregularity is handled is **unverified** here |
| **Lebel, Soize et al.**, HAL paper on statistical inverse identification (reference to be filled) | Companion statistical inverse-problem paper of the same group | As above; **unverified** |

All entries in B3 are user-supplied; their details have not been read in this repository.

---

## C. Bearing / axlebox-bearing / bearing-support stiffness identification

### C1. Railway axlebox bearings

| Ref | What it does | Identification from in-service ABA? |
|---|---|---|
| Sci. Rep. (2023), "Dynamic response of axle box bearing for high-speed train considering wheelset flexibility and polygonal wear" (authors given in one snippet as Guan, Deng, Wang; **partially verified**) | Forward model. At 300 km/h the 20th-order polygon excites 576.5 Hz, close to the 577 Hz flexible-wheelset 20th mode, and resonance raises bearing contact forces. | No (forward simulation). 10.1038/s41598-023-50177-2 (seen) |
| Li, T., Sun, W., Meng, Z., Huo, J., Dong, J., Wang, L. (2019), "Dynamic investigation on railway vehicle considering the dynamic effect from the axle box bearings", *Adv. Mech. Eng.* | Forward model coupling the axle-box bearing into vehicle dynamics. | No. 10.1177/1687814019840503 (seen in URL) |
| *MSSP* (2024), "A load estimation model for axle box bearings of high-speed trains based on vehicle dynamic response" (pii S0888327024006265) | Bearing–half-vehicle model plus Kalman filter to estimate **bearing loads**. Key model parameters must be tuned beforehand. | Loads, not stiffness. Authors **unverified** |
| Zheng, Z., Song, D., Zhang, W., Xu, X., Ma, C., Cui, W. (2025), "Dynamic response analysis of high-speed train axle box bearing by considering time-varying dynamic parameters", *MSSP* 224, 112119 (pii S0888327024010173) | Forward 2-DOF bearing model with time-varying load, radial clearance, contact damping and contact stiffness; compares outer-race defect vibration with varying-compliance (VC) vibration. Checked against one 1-s in-service high-speed signal (envelope line at 157 Hz plus 12 harmonics at 1294 r/min, the VC/roller-pass frequency). | No (forward model; no EKF, no rig, no identification). 10.1016/j.ymssp.2024.112119 (**full text verified**) |
| Li, Z., Chi, M., Cai, W., Zhou, Y. (2025), "An estimating methodology for the load of train axle box bearings", *High-speed Railway* | Kalman filtering with the maximum correntropy criterion (FMCC-DKF) for bearing load; robust to speed changes. | Loads only. 10.1016/j.hspr.2025.08.002 (seen) |
| *Vehicle System Dynamics* (2023), 10.1080/00423114.2023.2235031 | Bearing–vehicle coupled model with time-varying bearing stiffness. | Forward model. Authors **unverified** |
| Unidentified 2024 model study (seen only in a search summary) | Track irregularities affect axle-box bearing vibration more than internal clearance does. | Forward model. **Unverified** source. Relevant as a confound argument. |
| Review on axle-box bearing condition monitoring (various, e.g. *Machines* 2024) | Bearing diagnostics rely on envelope demodulation of defect frequencies, not on a support-resonance shift. | No |

No paper was found that identifies axlebox bearing (support) stiffness, or tracks a
bearing-support resonance shift, from in-service ABA, with or without unknown roughness. No
railway-specific "axlebox bearing looseness, resonance shift" detection paper was found
either. The nearest is a rotating-machinery study: Behzad, ICSV 2023, Sharif. Loose
housing/race fits cut equivalent stiffness by about 53 % and natural frequency by about 15 %.
Details **unverified**.

### C2. Rotor dynamics (for completeness)

| Ref | What it does |
|---|---|
| Tiwari, R., Lees, A.W., Friswell, M.I. (2004), "Identification of Dynamic Bearing Parameters: A Review", *Shock and Vibration Digest* 36(2), 99–124 | Review of time- and frequency-domain identification of bearing force coefficients, choice of excitation, and estimate uncertainty. |
| Sinha, J.K., Lees, A.W., Friswell, M.I. (2004), "Estimating unbalance and misalignment of a flexible rotating machine from a single run-down", *J. Sound Vib.* 272, 967–989 | Uses run-down (variable-speed) data to estimate unbalance, misalignment and a flexible foundation model. Tested on experimental data. 10.1016/j.jsv.2003.03.006 (seen). |
| Lees, A.W., Sinha, J.K., Friswell, M.I. (2004), "The Identification of the Unbalance of a Flexible Rotating Machine From a Single Run-down", *J. Eng. Gas Turbines Power* 126(2), 416–421 | Splits the run-down frequency range into bands and weights them, for foundations with many modes. |
| Mendoza-Larios, J.G., Barredo, E., Arias-Montiel, M., et al. (2021), "An Algebraic Approach for Identification of Rotordynamic Parameters in Bearings with Linearized Force Coefficients", *Mathematics* 9(21), 2747 | Algebraic identifier of bearing stiffness and damping using the vibration response only, at constant and variable speed. Numerical only. 10.3390/math9212747 (seen). |
| Parziale et al. (2024), *Sensors* 24(1), 207 (from the earlier `lit_review.md`) | Deterministic PINN for the support stiffness and damping of a Jeffcott rotor. |

In rotor dynamics, run-up and run-down identification relies on the **known, speed-synchronous
unbalance force**. Our problem is the reverse: the excitation is unknown and broadband
(roughness), and speed diversity serves to separate it from the TF.

---

## D. Frequency-domain likelihood with an unknown input spectrum

| Ref | Relevance |
|---|---|
| **Au, S.-K. (2011)**, "Fast Bayesian FFT Method for Ambient Modal Identification with Separated Modes", *J. Eng. Mech.* 137(3), 214–226 | Bayesian FFT OMA: a likelihood of FFT coefficients over a selected band, with the modal force PSD (assumed constant over the band) as a parameter, and fast computation for separated modes. 10.1061/(ASCE)EM.1943-7889.0000213 (seen). |
| **Au, S.-K. (2012)**, "Fast Bayesian ambient modal identification in the frequency domain, Part I: Posterior most probable value", *MSSP* 26(1), 60–75; Part II, "Posterior uncertainty", *MSSP* 26(1), 76–90 | Most probable value (MPV) algorithm and posterior covariance from the Hessian of the negative log-likelihood. |
| Hierarchical Bayesian OMA, arXiv:1908.06370 | Restates the Bayesian FFT model: FFT ordinates treated as independent, modal force PSD constant within the band. This is exactly the "nuisance PSD per band" structure. |
| Au, S.-K. (2016), "Insights on the Bayesian spectral density method for operational modal analysis", *MSSP* 66–67 | The Bayesian FFT and spectral-density approaches stop being equivalent at practical data lengths. |
| **Katafygiotis, L.S., Yuen, K.-V. (2001)**, "Bayesian spectral density approach for modal updating using ambient data", *Earthq. Eng. Struct. Dyn.* 30(8), 1103–1123 | Likelihood built on the statistics of spectral-density estimates. 10.1002/eqe.53 (seen). |
| Yuen, K.-V., Katafygiotis, L.S. (2001), "Bayesian time-domain approach for modal updating using ambient data", *Prob. Eng. Mech.* 16(3), 219–231 | Time-domain counterpart. 10.1016/S0266-8920(01)00004-2 (seen). |
| Pintelon, R., Schoukens, J. (2006), "Frequency domain maximum likelihood estimation of linear dynamic errors-in-variables models" (TLS/EIV workshop, Leuven); Schoukens, Pintelon, Renneboog (1989) | Frequency-domain ML with noisy or unknown inputs. |
| Pintelon, R., Guillaume, P., Schoukens, J. (2007), "Uncertainty calculation in (operational) modal analysis", *MSSP* 21, 2359–2373 | Uncertainty bounds in OMA. Whether this paper is ML-based is **unverified**; one review calls it perturbation-based. |
| Linköping report 2131 (1999), on CARMA/Whittle | Describes the Whittle estimator as a frequency-domain approximation to time-domain ML, with a long history in ARMA estimation. Authors **unverified**. |
| USM (Chile) thesis | Whittle likelihood for continuous-time system identification compared with frequency-domain ML. |

No paper was found that applies a Whittle or Bayesian-FFT likelihood to ABA or to
vehicle–track identification. The likelihood itself is standard. Au's Bayesian FFT, with the
modal-force PSD as a nuisance parameter, is the prior art to cite for that structure.

---

## Closest prior art

| # | Paper | What it shares with our method | What it does **not** do |
|---|---|---|---|
| 1 | Carrigan & Talbot (2023), *MSSP* 192, 110232 (plus the Cambridge LNME paper and ISMA 2022 #434) | ABA only, unknown roughness, and estimates a **structural stiffness (track/pad, from the P2 peak) together with the roughness spectrum** | Targets track stiffness at the P2 resonance, not bearing-support stiffness at about 500–650 Hz. Fits the peak deterministically, section by section, then deconvolves. No multi-pass likelihood. Speed diversity is not used as the identifiability mechanism. No uncertainty quantification seen. |
| 2 | Pieringer & Kropp (2022), *Appl. Acoust.* 193, 108760 | Model-based roughness from ABA. Shows roughness errors are dominated by stiffness uncertainty. | States joint estimation of track parameters and roughness as **future work**. No vehicle-bearing parameters. |
| 3 | Stoura et al. (2023), *SCHM*, 10.1155/2023/8855542 (and Dertimanis et al. 2020) | Bayesian joint input (roughness) and state estimation from on-board ABA. Updates some vehicle-model parameters (UKF). | Vehicle parameters are calibrated from diagnostic-vehicle data. Time-domain profile estimation. No bearing-support stiffness, no speed-diversity identifiability, no Whittle likelihood. |
| 4 | Jin, Yang et al. (2021), *Eng. Struct.* 230, 111688 (and the DBE 2023 speed-subtraction paper) | **Uses passes at different speeds to cancel roughness** (fixed in wavenumber) from a structural frequency (fixed in frequency) | Road vehicle and bridge frequencies. Subtraction or residuals, not a likelihood. No roughness spectrum estimate. No vehicle-parameter identification. |
| 5 | Keenahan, Ren, OBrien (2019); Ren et al. (IJSSD) fleet concept; Liu et al. (2024), *Appl. Sci.* 14, 10310 | **Jointly estimate road profile and vehicle properties** from several passes or vehicles | Road vehicles, low frequency. Keenahan et al. recover only *relative* vehicle properties, which matches our scale-ambiguity concern (roughness level against TF gain). Liu et al. use the axle time lag, not speed. No railway, no bearing. |
| 6 | Au (2011, 2012), Bayesian FFT OMA | Frequency-domain likelihood with an unknown excitation PSD as a nuisance parameter | Stationary ambient structures. No moving load, no speed-to-wavenumber mapping, no multi-pass pooling across speeds. |
| 7 | Hoelzl et al. (2022) arXiv:2209.12899; Shen et al. (2023) *MSSP* 204, 110730; LPV-AR chapter (IMAC) | Structural stiffness from ABA; speed-aware processing (order tracking, LPV scheduling) | Track stiffness, not bearing stiffness. No explicit roughness-spectrum nuisance model (Shen: **unverified**). |

---

## Novelty caveats by method component (overlap, paper by paper)

Each row is one ingredient of our method, the papers that overlap with it, **what exactly overlaps**,
and what differs. "Snippet" means only an abstract, highlight or search summary was read. Nothing
here was read in full text.

### C1. Target: bearing-support stiffness k_B0 (support resonance about 450–700 Hz) from in-service ABA
| Paper | Overlap | Difference | Evidence |
|---|---|---|---|
| Zheng et al. 2025, *MSSP* 224, 112119 (10.1016/j.ymssp.2024.112119) | Axlebox bearing with time-varying contact stiffness and damping; VC vibration lines at the roller-pass order in in-service ABA | Forward model only: no identification, no roughness treatment, no multi-pass | full text verified |
| *MSSP* 2024, "A load estimation model for axle box bearings ..." (pii S0888327024006265); Li, Chi, Cai, Zhou 2025 (*High-speed Railway*) | Bearing–vehicle model inverted from vehicle response with a Kalman filter | Estimates bearing **loads**; stiffness is tuned beforehand, not identified | snippet |
| Sci. Rep. 2023 (10.1038/s41598-023-50177-2); Li et al. 2019 (*Adv. Mech. Eng.*); *VSD* 2023 (10.1080/00423114.2023.2235031) | Axlebox bearing in a coupled vehicle model, bearing resonance in the few-hundred-Hz band | Forward simulation only | snippet |
| Behzad, ICSV 2023 (rotating machinery) | Loose housing fit lowers equivalent stiffness (≈53%) and natural frequency (≈15%): the physical basis for "stiffness loss as health index" | Not railway; no identification method | snippet; unverified |
| Parziale et al. 2024 (*Sensors* 24, 207) | Support stiffness and damping identified (Jeffcott rotor, PINN) | Known excitation, rig/simulation, no roughness | from `lit_review.md` |

**No paper was found that identifies bearing-support stiffness from in-service ABA.** The blind
spot is Chinese-language work on axle-box bearings.

### C2. Joint estimation of a structural stiffness and the roughness spectrum from ABA alone
| Paper | Overlap | Difference | Evidence |
|---|---|---|---|
| **Carrigan & Talbot 2023**, *MSSP* 192, 110232; Cambridge LNME chapter; ISMA 2022 #434 | **Same problem structure**: unknown roughness, a stiffness parameter estimated from the ABA spectrum by fitting a model TF to a resonance peak (P2), then the roughness spectrum by deconvolution. Wheel roughness removed with a comb filter | Track/pad stiffness at P2 (≈50–150 Hz), not bearing support. Sequential deterministic peak fit per section, not a joint likelihood. No CRB or coverage seen. Speed not used for identifiability (one snippet: measured FRF largely speed-independent) | snippets of the abstract and repository record; **full text needed to rule out multi-speed use** |
| **Pieringer & Kropp 2022**, *Appl. Acoust.* 193, 108760 | Model-based roughness from ABA; quantifies that stiffness error (rail pad, 20% gives 3.5 dB) contaminates roughness | Track parameters assumed known; **joint estimation stated as future work** | snippet (abstract) |
| **Stoura et al. 2023**, *SCHM*, 10.1155/2023/8855542; Dertimanis et al. 2020 (IMAC) | Roughness as an unknown input estimated jointly with the vehicle state; **some vehicle parameters updated (UKF)** | Parameters calibrated from diagnostic-vehicle data. Time-domain profile. Low-frequency vehicle model; no bearing, no speed diversity | snippet (abstract) |
| Shen, Zhang, Dollevoet, Zoeteman, Li 2023, *MSSP* 204, 110730 | Rail-pad and ballast stiffness **and the irregularity level** identified jointly from ABA, through a Gaussian-process library of simulations; uses bands including 400–700 Hz | Track parameters only, no vehicle-side parameters; irregularity as one level parameter, not a spectrum with free sub-band levels; three speeds estimated separately, so speed diversity is not used for identifiability | user's full-text reading (2026-10-15) |
| "Simultaneous identification of the frequencies and track irregularities of high-speed railway bridges from vehicle vibration data", *MSSP* 2020/21 | Joint structural frequencies and track irregularity from vehicle response (Kalman) | Bridge frequencies, not vehicle parameters; single speed | snippet; authors unverified |

### C3. Roughness as a wavenumber-domain spectrum with free per-band levels (nuisance)
| Paper | Overlap | Difference | Evidence |
|---|---|---|---|
| Carrigan, Talbot (Fidler), "On the derivation of rail roughness spectra from axle-box vibration: development of a new technique" | A **stochastic frequency-domain inverse method** for roughness *wavelength* spectra with speed compensation | Roughness is the target and the TF is assumed or modelled; no parameter identification seen | snippet; venue/year unverified |
| ISO 3095 / EN 15610 practice; Pieringer & Kropp | One-third-octave wavelength band levels as the roughness descriptor | Descriptor only | standard |
| Au 2011/2012 (Bayesian FFT) | An unknown **flat PSD per frequency band** as a nuisance parameter in an FFT likelihood | Bands in frequency, for ambient forces; no wavenumber mapping | snippet |

### C4. Speed diversity as the identifiability mechanism (roughness fixed in wavenumber, resonance fixed in frequency)
| Paper | Overlap | Difference | Evidence |
|---|---|---|---|
| **Jin, Yang, Dimitrakopoulos, Paraskeva, Katafygiotis 2021**, *Eng. Struct.* 230, 111688 | **Exactly this physical idea**: two traverses at different speeds; a transformed residual cancels road roughness and leaves the bridge frequencies | Road vehicle over a bridge. Subtraction, not likelihood. No roughness estimate, no vehicle parameters, two speeds | snippet |
| *Dev. Built Environ.* 14 (2023), PSD-based drive-by damage; T&F chapter "Mitigation of unwanted effects in drive-by acceleration data" | Subtract responses at different speeds in the **spatial domain** to remove roughness | Same differences as above | snippets; authors unverified |
| Yang, Zhang, Qian, Wu 2018 (*IJSSD*), contact-point response | Two axles or vehicles cancel roughness | Axle spacing, not speed | snippet |
| Wang et al. 2024, *Sensors* 24, 3804; Hoelzl et al. 2022, arXiv:2209.12899; LPV-AR IMAC chapter | Speed-aware ABA processing: order tracking, angular resampling, speed-scheduled models | Speed used to *align* or *schedule*, not to separate roughness from a TF | snippets |
| Lanzillo 2023 (MSc, PoliMi); Yu et al. 2025 (*Measurement* 249) | Note that ABA-derived roughness disperses with speed near wheel–rail resonances, i.e. speed changes reveal TF error | Treated as an error source, not exploited | snippets |

### C5. Frequency-domain (Whittle) likelihood with unknown input spectrum; profile/Fisher uncertainty
| Paper | Overlap | Difference | Evidence |
|---|---|---|---|
| **Au 2011** (*JEM* 137(3)); **Au 2012** (*MSSP* 26(1), Parts I–II) | Likelihood of FFT ordinates treated as independent, unknown force PSD as a parameter, posterior covariance from the Hessian. **Our likelihood is structurally the same.** | Stationary ambient structures, single setup; no speed-to-wavenumber map, no multi-pass pooling | snippets |
| Katafygiotis & Yuen 2001 (*EESD* 30(8)); Yuen & Katafygiotis 2001 (*PEM*) | Bayesian spectral-density likelihood for modal updating | Same differences | snippets |
| Pintelon & Schoukens (frequency-domain ML, errors-in-variables) | Frequency-domain ML with noisy or unknown inputs | Measured-input setting | snippets |
| — | **Not found**: any Whittle or Bayesian-FFT likelihood applied to ABA or vehicle–track parameter identification | — | — |

### C6. Joint estimation across many passes or vehicles; scale ambiguity between excitation level and TF gain
| Paper | Overlap | Difference | Evidence |
|---|---|---|---|
| **Keenahan, Ren, OBrien 2019** (UCD) | Several vehicles over one profile jointly give the profile; **only relative vehicle properties are identifiable** without prior information (the same gain ambiguity our per-band level nuisance creates; we break it with a known physical parametrisation and speed/payload diversity) | Road, low frequency, time-domain optimisation | snippet |
| Ren, Feng, OBrien, Li, He (*IJSSD*), fleet concept | Profile and vehicle properties from a fleet | Same differences | snippet; year not seen |
| **Liu, Guo, Yang, Liu 2024**, *Appl. Sci.* 14, 10310 | Vehicle parameters (including tyre stiffness) and road roughness identified jointly | Uses the front–rear axle time lag, not speed; EKF with unknown input; half-car | snippet |
| **An et al. 2024**, *Struct. Multidiscip. Optim.* 67, 164 | Road-vehicle parameters and road roughness identified jointly, **Bayesian, in the frequency domain** | Road vehicle; suspension-band targets (well below an axle-box support band); roughness handling to be checked against our per-sub-band levels | user-supplied (2026-10-15); full text not read here |
| **Guo et al. 2026**, *Struct. Control Health Monit.* | Road-vehicle joint parameter and roughness identification (same group as Liu et al. 2024) | Road vehicle, suspension band | user-supplied (2026-10-15); details not read here |

### C7. Payload measured per pass (WIM) entering load-dependent bearing and contact stiffness
No overlapping identification paper was found. Load dependence of Hertzian contact and roller-bearing
stiffness is textbook. Carrigan & Talbot and Pieringer & Kropp treat axle load as known. **Not
found** is not the same as absent.

### C8. Physics-informed learning on ABA or bearing supports (matters only if a surrogate is kept)
| Paper | Overlap | Difference | Evidence |
|---|---|---|---|
| PD-SOVNet, arXiv:2604.06620 (2026) | Physics-driven operator network on axle-box vibration | Wheel polygonal roughness, not bearing stiffness | title only |
| Parziale et al. 2024 | PINN identification of support stiffness | Rotor rig, deterministic | as above |

### C9. Confounds a reviewer will cite (not novelty threats, but they bound the claim)
- **Wheel polygon orders near the support resonance.** Sci. Rep. 2023 (10.1038/s41598-023-50177-2): 20th order at 576.5 Hz at 300 km/h. Polygon orders scale with speed like roughness but are *periodic per revolution*, so they appear as lines, not as a broadband wavenumber spectrum. Carrigan & Talbot remove them with a comb filter.
- **Wheelset flexible modes in the band.** Same paper: about 577 Hz. Our FE model contains the axle modes; wheel-web modes are outside L1-lin.
- **Track and rail-pad stiffness variability.** Pieringer & Kropp: dominant roughness-error source. In our model it enters through k_H and the rail oscillator; the robustness scan covered contact stiffness ±30%, but not rail-pad variation between passes.

---

## Stop question

**Is there already a published method that jointly estimates rail roughness (or its spectrum) and identifies bearing-support / axlebox bearing stiffness (or the vehicle's high-frequency support resonance) from ABA, using speed variation across passes?**

**Answer: NO.** This rests on what could be reached here: snippets, no full texts, and no Chinese- or Japanese-language search. The individual pieces are published, as listed below.

- **Joint roughness spectrum and a structural stiffness from ABA: yes, but for *track* stiffness.**
  - Carrigan & Talbot (2023) and the related Cambridge papers fit the P2 peak to get track stiffness, then derive the roughness spectrum.
  - The Chalmers paper (Pieringer & Kropp 2022) names simultaneous estimation as an open need.
- **Vehicle-parameter updating with roughness as an unknown input: yes, partly.**
  - Stoura et al. (2023) do this, but calibrate the vehicle parameters with diagnostic-vehicle data and do not target bearing stiffness.
- **Speed diversity across passes to separate roughness from a fixed-frequency resonance: yes, but only in drive-by bridge monitoring.**
  - Jin, Yang et al. (2021); DBE 2023; the Taylor & Francis chapter.
  - All use subtraction or residuals, not a likelihood, and none identify vehicle parameters.
- **Bearing-support stiffness from in-service ABA: not found.**
  - Railway axlebox-bearing papers are forward models (including Zheng et al. 2025, with time-varying contact parameters) or load estimators; none identifies the support stiffness.
- **Frequency-domain likelihood with a nuisance input PSD: yes, in OMA** (Au's Bayesian FFT; Katafygiotis & Yuen). It has not been applied to ABA or vehicle–track identification.

**Novelty statement (fixed 2026-10-15, user's wording; use only this):**

> To our knowledge, this is the first method to identify the vertical stiffness of the axle-box bearing
> support from in-service axle-box acceleration without measuring rail roughness. The support resonance
> and the roughness are separated by pooling passes at different speeds and payloads in a single
> debiased Whittle likelihood, in which roughness levels are free nuisance parameters. Joint estimation
> of vehicle or track parameters with unknown excitation has been studied for track stiffness
> (Carrigan & Talbot 2023; Shen et al. 2023) and for road-vehicle suspensions (Liu et al. 2024; An et
> al. 2024). There, roughness is handled by deconvolution, a single level parameter, or axle time lags,
> and the targets lie below the axle-box support band.

The paper must also cite and position against: Pieringer & Kropp (2022), the stated open problem;
Stoura et al. (2023), Bayesian joint input and parameters; Jin, Yang et al. (2021) and the
speed-subtraction drive-by papers, the speed-diversity concept; Keenahan et al. (2019), relative
identifiability only; Guo et al. (2026); Lebel, Soize et al. (2019 and the HAL paper), rail-vehicle
suspension identification; Au (2011, 2012), the likelihood structure.

Do not claim novelty for:
- joint parameter and roughness (or unknown-excitation) estimation in general: track stiffness
  (Carrigan & Talbot; Shen et al.), road vehicles (Liu et al.; An et al.; Guo et al.), rail-vehicle
  suspensions (Lebel, Soize et al.);
- "using speed to separate roughness from structure" in general (drive-by precedent);
- a frequency-domain Bayesian or likelihood treatment with unknown excitation in general (An et al.
  2024; Au).

**Risks a reviewer may raise, from the snippets:**
1. **Wheel roughness.** Polygon orders are also speed-proportional and can sit near 500–650 Hz; the Sci. Rep. 2023 paper puts the 20th-order polygon at 576.5 Hz at 300 km/h. Carrigan & Talbot use a comb filter or synchronous averaging for this.
2. **Other fixed-frequency features in the same band.** Wheelset flexible modes (around 577 Hz in that paper), the pinned-pinned resonance (around 1 kHz), and sleeper-passing frequency (speed-proportional).
3. **Track-stiffness variability** moves the P2 band (Pieringer & Kropp: rail-pad stiffness is the dominant error source).

**Before submission, confirm with library access:**
- the full text of Carrigan & Talbot (2023), whether they exploit multiple speeds;
- whether any of the 2024–2025 Chinese axle-box bearing papers identify bearing stiffness from ABA (Shen et al. 2023 resolved 2026-10-15: track parameters and irregularity level only, three speeds estimated separately);
- the full texts of An et al. (2024) and Guo et al. (2026), how they parametrise roughness;
- the titles and bibliographic details of the Lebel, Soize et al. papers.

---

## Queries run (web search)

1. estimation of rail roughness from axle box acceleration Chalmers Carlberger Torstensson Nielsen
2. "axle box acceleration" rail roughness indirect measurement transfer function vehicle-track model
3. Molodova Li Núñez Dollevoet axle box acceleration squats measurement 2014
4. Bocciolone corrugation axle box acceleration measurement Di Gialleonardo Corradi
5. Pieringer Kropp "Model-based estimation of rail roughness from axle box acceleration" Applied Acoustics 2022 DOI
6. Carrigan Talbot rail roughness spectra axle box acceleration track stiffness wheel roughness synchronous averaging
7. squats rail defects axle box acceleration Molodova Li Dollevoet
8. Faccini Di Gialleonardo Bocciolone corrugation monitoring axlebox acceleration Applied Sciences 2023 DOI
9. "On the derivation of rail roughness spectra from axle-box vibration" Carrigan Talbot Fidler journal DOI
10. Cambridge Carrigan Talbot flexible wheelsets comb filter rail roughness axle box acceleration frequency-domain
11. "Rail Roughness Identification Via On-Board Acceleration Data and Bayesian Filtering"
12. "Calibration of transfer functions on a standstill vehicle for on-board indirect measurements of rail acoustic roughness"
13. De Rosa Alfi Bruni estimation of rail irregularity from vehicle measurements Kalman filter axlebox Politecnico di Milano
14. Salvador Naranjo Insa Real Ferreira axlebox acceleration track condition monitoring frequency
15. Kraft indirect rail roughness measurement axle box acceleration acoustic roughness ISO 3095 on-board
16. Tanaka Shimizu axle box acceleration rail corrugation estimation inverse analysis Railway Technical Research Institute
17. axle box acceleration track stiffness estimation unknown rail roughness P2 resonance (extended)
18. simultaneous identification track irregularity and vehicle parameters from on-board measurements (extended)
19. different vehicle speeds separate rail roughness from transfer function axle box acceleration wavelength frequency (extended)
20. "A new method to derive rail roughness from axle-box vibration accounting for track stiffness variations and wheel-to-wheel coupling" MSSP (extended)
21. ISMA 2022 "Monitoring rail roughness using axle-box accelerometers" authors
22. "Vold-Kalman" order tracking axle box accelerations railway stiffness assessment authors
23. isma2022 Contribution_434 rail roughness axle-box accelerometers track stiffness 62 m sections FRF fit P2 (extended)
24. "Quantitative Detection of Vertical Track Irregularities under Non-Stationary Conditions with Variable Vehicle Speed" Sensors 2024
25. drive-by bridge monitoring road roughness elimination two connected vehicles residual contact response Yang
26. drive-by bridge frequency identification multiple vehicle speeds remove road roughness effect speed-dependent peaks (extended)
27. Malekjafarian OBrien drive-by railway track stiffness estimation axle box acceleration Quirke Cantero
28. "transformed residual" vehicle response two traverses different speeds bridge road roughness
29. drive-by bridge identification vehicle passes at different speeds road roughness spatial domain cancels bridge frequency fixed
30. Quirke Cantero OBrien Bowe "Drive-by detection of railway track stiffness variation using in-service vehicles" ...
31. Engineering Structures 2020 111688 bridge frequency identification two traverses vehicle different speeds residual response authors
32. "subtracting responses at different speeds" spatial domain drive-by bridge damage quarter-car Developments in the Built Environment 2023 authors
33. axle box bearing stiffness identification from axle box acceleration railway wheelset (extended)
34. axlebox bearing support stiffness high-frequency resonance 500 Hz wheelset vertical vibration model (extended)
35. railway axle box bearing looseness clearance stiffness reduction vibration resonance frequency shift detection
36. "Evaluating railway track stiffness using axle box accelerations: A digital twin approach" authors
37. railway vehicle suspension parameter identification unknown track irregularity axlebox acceleration output-only (extended)
38. bearing stiffness damping identification rotor run-up variable speed unbalance response frequency domain
39. Tiwari Lees Friswell "Identification of dynamic bearing parameters: a review" Shock and Vibration Digest 2004
40. Lees Sinha Friswell estimation of foundation parameters and unbalance run-down rotor machine JSV
41. Au Bayesian FFT operational modal analysis unknown modal force PSD posterior MSSP
42. Pintelon Schoukens frequency domain maximum likelihood estimation unknown input noise errors-in-variables system identification
43. Au "Fast Bayesian FFT method for ambient modal identification with separated modes" JEM 2011
44. Whittle likelihood structural system identification output-only stochastic excitation frequency domain
45. Pintelon Guillaume Schoukens "Uncertainty calculation in (operational) modal analysis" MSSP 2007 maximum likelihood
46. Yuen Katafygiotis Bayesian spectral density approach modal updating ambient data 2001 PEM
47. Stoura Dertimanis Chatzi "A Model-Based Bayesian Inference Approach for On-Board Monitoring of Rail Roughness Profiles" SCHM 2023 abstract
48. joint input-parameter estimation rail roughness track parameters axle box acceleration Bayesian filter dual Kalman (extended)
49. Au "Fast Bayesian ambient modal identification in the frequency domain, Part I: Posterior most probable value" 2012
50. "On-Board Monitoring of Rail Roughness via Axle Box Accelerations of Revenue Trains with Uncertain Dynamics" authors abstract
51. rail pad stiffness estimation axle box acceleration unknown roughness Chalmers simultaneous extraction track parameters roughness
52. Wang Li Núñez TU Delft track stiffness axle box acceleration wavelet ballast stiffness frequency
53. Shen Zhang Dollevoet Zoeteman Li digital twin track stiffness axle box accelerations railpad sleeper ballast abstract Bayesian optimization
54. axle box acceleration repeated passes multiple train speeds roughness wavelength speed-invariant resonance fixed frequency identification (extended)
55. Yang Y.B. contact-point response vehicle scanning method bridge frequencies removing vehicle frequency 2018 JSV
56. road profile and vehicle parameters simultaneous identification multiple passes different speeds drive-by Bayesian (extended)
57. cepstrum separate road roughness excitation from vehicle transfer function different speeds
58. "A Bayesian framework-based vehicle parameters identification method with unknown road excitation" SMO abstract
59. Keenahan Ren OBrien determination of road profile using multiple passing vehicle measurements cross entropy unknown vehicle properties
60. "Bridge Profile and Vehicle Property Determination Using Vehicle Fleet Monitoring Concept" authors journal
61. Applied Sciences 2024 simultaneous identification vehicle parameters and road roughness extended Kalman filter unknown excitation mutual iteration
62. mdpi Applied Sciences 14 22 10310 vehicle parameters road roughness EKF-UI half-vehicle tire stiffness title authors
63. operational modal analysis railway vehicle in-service varying speed track excitation harmonic order components separation bogie
64. identification of axle box bearing stiffness high-speed train inverse method measured vibration (extended)
65. wheelset axle box resonance frequency in-service monitoring bearing degradation axle box acceleration spectrum peak shift
66. "A load estimation model for axle box bearings of high-speed trains based on vehicle dynamic response" authors MSSP 2024
67. "Dynamic response analysis of high-speed train axle box bearing by considering time-varying dynamic parameters" authors EKF equivalent stiffness
68. "axle box acceleration" identify vehicle high-frequency parameters wheelset bearing stiffness rail roughness unknown multiple speeds (extended)
69. frequency response function vehicle-track system estimated from in-service axle box acceleration spectra at different speeds output-only (extended)
70. "Axle Box Accelerometer Signal Identification and Modelling" LPV-AR vehicle speed scheduling authors
71. rail roughness LSTM deep learning axle box acceleration inverse estimation Ma Zhang Wang 2023
72. Jeong KTX axle box acceleration rail roughness corrugation measurement Korea Lee Hong
73. "Experimental study of the use of a transfer function to find rail corrugation from axle-box accelerations" Measurement 2025 authors
74. "Evaluating Rail Surface Roughness from Axle-Box Acceleration Measurements: Computational Metrology Approach" authors year
75. Kojima Tsunashima axle box acceleration track irregularity estimation in-service vehicle Japan
76. Whittle likelihood vehicle response road roughness PSD parameter estimation
77. Bayesian identification track parameters and rail roughness spectrum from axle box acceleration multiple train runs uncertainty quantification (extended)
78. vehicle parameter identification from response power spectral density unknown track irregularity spectrum maximum likelihood railway
79. Pieringer Kropp follow-up axle box acceleration simultaneous estimation rail pad stiffness and roughness 2024 2025
80. EN 15610:2019 indirect method rail roughness measurement vehicle-based axle box annex
81. Molodova Li Dollevoet "Axle box acceleration: Measurement and simulation for detection of short track defects" Wear 2011
82. bearing support stiffness identification output-only operational modal analysis rotor variable speed unknown excitation
83. Malekjafarian McGetrick OBrien review indirect bridge monitoring using passing vehicles Shock and Vibration 2015
84. Mathematics 2021 rotor-bearing identifier vibration response only constant and variable speed ... authors
85. "Whittle" likelihood operational modal analysis modal parameters estimation ambient vibration
86. axle box acceleration spectrum peaks independent of speed resonance versus peaks proportional to speed wavelength excitation analysis
87. wheel-rail contact resonance unsprung mass axle box frequency identification in-service measurements varying axle load speed
88. 10.1177/0954409720923213 axle box bogie response measuring track unevenness P2 resonance title authors
89. Carrigan Talbot "development of a new technique" ... stochastic frequency-domain inverse method speed compensation 2019 conference
90. "On-board and quantitative monitoring method of rail corrugation in the presence of wheel polygon" Measurement 2025
91. Yang Lin Yau 2004 extracting bridge frequencies from dynamic response of passing vehicle JSV
92. Bayesian FFT modal identification moving vehicle response bridge road roughness drive-by Au

Direct fetches attempted, all of which failed:
- WebFetch: research.chalmers.se, repository.cam.ac.uk, ruja.ujaen.es, doaj.org, mdpi.com, and the Semantic Scholar API.
- curl: the hosts listed at the top, all returning 403.

## Spot check by the main session (2026-10-11)

I ran five more web searches, which reached snippets only, like the searches above. They covered:
bearing-stiffness identification from ABA with unknown roughness and multiple speeds; joint
estimation of roughness and the transfer function across speeds; resonance shift in axlebox
bearing support stiffness; and Whittle or Bayesian-FFT likelihoods applied to train passages.

None of them found a method that identifies bearing-support stiffness jointly with roughness, or one
that uses speed diversity for that purpose. The closest results were again:
- Carrigan & Talbot (MSSP 2023): track stiffness from the P2 peak;
- Pieringer & Kropp (Appl. Acoust. 2022): simultaneous estimation named as future work;
- Hoelzl et al. (arXiv:2209.12899): Vold-Kalman order tracking.

One new nearby item, not in the tables above: "PD-SOVNet: a physics-driven second-order vibration
operator network for estimating wheel polygonal roughness from axle-box vibrations", arXiv:2604.06620
(2026; title and listing only, not read). It is a physics-informed learning approach to wheel
roughness from ABA, so it should be cited if the paper keeps any physics-informed surrogate. It does
not identify bearing stiffness.
