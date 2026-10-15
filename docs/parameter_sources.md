# Parameter sources: representative freight wagon (Y25, 22.5 t) on ballasted 60E1 track

Sourcing round 1: 2026-10-15, four web-search agents; round 2 (full-text checks) is recorded at the end.
Rules: a value counts as sourced only if it was seen in a search result or fetched page. In round 1 no
page could be fetched (DNS failures, proxy refusals), so **every value below was seen in a search-result
snippet only**, not checked against the full text. "Assumed, swept" = not found; varied over the stated
range in `results/p4/sweep.json`. Used values are in `config/params.yaml` and `config/track.yaml`.

## Wheelset and axle

| Parameter | Used | Range seen | Source (snippet) |
|---|---|---|---|
| Axle length | 2180 mm | 2180–2187.6 mm | BA004 wheelset for Y25 bogie, railwayspare-parts.com listing ("total axle length 2180 (+1/-1) mm"); Type D axle 2187.575 mm (same vendor, paraphrase) |
| Journal diameter | 130 mm | 130 (EN), AAR 144.5–157.2 | BA004 listings; Unirail BA004 ("Ø130х191mm according to EN 13261") |
| Wheel-seat diameter | 200 mm | 192–200 | BA004 listing ("nominal wheel pressing-on the axle diameter f 200 mm") |
| Axle body diameter | 173 mm | 173 (+2/−0) | BA004 listing |
| Dust-guard collar diameter, section boundaries | 160 mm; as before | – | assumed |
| Axle-box centre distance 2b | 2000 mm | – | Bižić M., Petrović D. (2021), "Analytical calculation of strength of freight wagon axle in accordance with European standards", Mechanics Transport Communications 19(3), article 2113 (venue corrected in round 2) ("2b=2000 mm") |
| Rolling-circle distance 2s | 1500 mm | – | Bižić & Petrović (2021) ("2s=1500 mm") |
| Wheel diameter (new / worn) | 920 mm (r0 = 0.46 m) | 840–920 mm | Bižić & Petrović (2021); Unirail BA004 ("Minimal repair diameter: Ø840mm"); railway-technology.com Y25 bogie |
| Wheel mass | 304 kg | – | Unirail BA004 and BA 092 pages ("Nominal weight: 304kg. Material: ER7") |
| Axle mass | (from FE geometry) | 390 kg (EN axle) | Unirail BA004 |
| Wheelset mass | – | 998–1526 kg | Unirail BA004 998 kg; Bosso, Magelli & Zampieri (2023) Appl. Sci. 13(3) 1318 1080 kg (Y25L, 22.5 t); Dusza (2023) Rail Vehicles 1400 kg; Bižić & Petrović (2021) 1350 kg; others |
| Wheel diametral inertia | 20 kg m² | 10–30 swept | assumed, swept (single-wheel inertia not found; wheelset roll inertia 656–903 kg m² seen) |
| Wheelset modal damping | 1% | 0.1–2% | Chaar N. (2007), KTH doctoral thesis TRITA AVE 2007:17 (round 2: "measured damping ratios for the first torsion and first and second bending modes (Table 2-1) are less than 2%"; round 1 had "less than 1%", not confirmed); IPME paper (citation incomplete) "0.1 to 1.0 %" |
| First bending frequency (damping reference) | 96 Hz | 96–115 Hz | Sci. Rep. (2025) s41598-025-15781-4 ("first-order vibration modal frequency of the wheelset (96 Hz)"); Mu et al. (2021) Shock Vib. 4677851 (115 Hz) |
| Unsprung mass per wheelset | (model: axle + wheels + axleboxes) | 1355 kg (Y25, 920 mm), 1610 kg (disc brakes) | RIVAS D5.5 (2013); Nielsen et al. (2015) IJRT 3(1) 17–39 |
| Unsprung-mass uncertainty (1σ) | 4% | – | SKF Evolution, "New axlebox concept for heavy loads" ("around 20 kg per axlebox ... unsprung weight of the wheelset by around 4 %") |

## Axlebox, bearing and suspension

| Parameter | Used | Range seen | Source (snippet) |
|---|---|---|---|
| Axlebox mass | 100 kg | 100–158.4 kg | Dusza, Gołofit-Stawińska, Zboiński (2024), Appl. Sci. 14(11) 4545 (Y25 model: axlebox 100 kg); Bustos, Rubio, Castejón, García-Prada (2025), Adv. Mech. Eng. 17(9) ("Axle box mass 158.42 kg") |
| Effective support stiffness k_B0 | 1.0e9 N/m | 0.5–3e9 swept | **assumed, swept**. Indications: "total supporting stiffness of 7.6·10^8 N/m" (Bustos et al. 2025, meaning unclear); adapter pad ≥ 5e6 lb/in (≥ 8.8e8 N/m) to 3e7 lb/in (5.3e9 N/m), US 9,580,087 (three-piece truck design target) |
| Bearing damping c_B | 6740 N s/m | 3000–12000 swept | **assumed, swept** (round 2 could not find the round-1 value in Li T. et al. 2019, Adv. Mech. Eng. 11(4), doi 10.1177/1687814019840503: the parameter is defined there, the value was not seen) |
| Primary vertical stiffness k_p | 1.017e6 N/m | 0.98–2.6e6 N/m | Dusza M. (2023), "Freight car model with Y25 bogies stability analysis", Rail Vehicles 2023(3-4) 13–24, doi 10.53502/RAIL-175725 ("1017 kN/m empty / 2280 kN/m loaded"; per axlebox or per spring set not resolved; not confirmed in Dusza et al. 2024); EP 1484228 A1 (Y25 spring set "980N/mm tare and 2600N/mm laden") |
| Primary damping c_p | 1e4 N s/m | 5e3–5e5 swept | **assumed, swept**; heavy-haul freight car "preferable primary vertical damping was 50–500 kN·s/m" (Yang, Li & Huang 2011, J. Southwest Jiaotong Univ.) |
| Bearing geometry (health check) | z 21, l 45 mm, D 23 mm, d_m 180.5 mm, α 10° | z 17–23, D 21.4–26.5 mm | Guan, Deng & Wang (2023) Sci. Rep. 13 (130 mm-bore high-speed TRB, proxy); Liu & Du (2020) IJAV 25(4); Sun et al. (2026) Results Eng. 29 (353130B: 23 rollers, 21.384 mm); Zhao et al. (2024) IJMSD 4(2) |
| Initial diametral clearance | 20 µm | 0–50 µm swept | **assumed, swept**; mounted axial endplay 0.001–0.015 in (Timken AP manual), conversion to radial clearance not sourced |
| Payload range | 5.5–22.5 t | – | 22.5 t axle load (railway-technology.com, Y25); empty axle load 5.5 t assumed |

## Rail, track, contact, layout

| Parameter | Used | Range seen | Source (snippet) |
|---|---|---|---|
| 60E1 area / I / mass | 76.70 cm², 3038.3 cm⁴, 60.21 kg/m | – | ArcelorMittal 60E1 datasheet (EN 13674-1); British Steel rail profiles datasheet; Valente |
| Rail shear coefficient | 0.40 | 0.34–0.40 | TU Delft thesis (0.4); UIC60 0.393 (attribution weak); CT23 Table 1 0.34 (BS113A) |
| Rail pad stiffness | 200 MN/m per pad | 80–800 MN/m | Thompson, Jones, Waters & Farrington (2007) Appl. Acoust. 68(1) 43–57 ("rail pad stiffness ... of 200 MN/m per pad"); EUROBOLT optimal track 80 kN/mm (Nova chapter); 800/120 MN/m (Thompson et al., attribution weak) |
| Sleeper spacing | 0.60 m | 0.60–0.65 m | EUROBOLT optimal track (Nova chapter); CT23 Table 1 |
| Foundation stiffness per unit length k_f | 333 MN/m² | 123–1333 MN/m² | derived: pad stiffness / spacing (pad modulus as defined in the PWI Guide to Track Stiffness) |
| Foundation loss factor | 0.2 | 0.1–0.25 | pad loss factors 0.16 (Thompson et al. 2007 table), 0.25 (rolling-noise models), ~0.1–0.2 (pad types) |
| Linearised contact stiffness k_H0 | 1.4e9 N/m | 1.4–2.3e9 N/m | "between 1,400 and 2,300 kN/mm" (ASCE conference paper, attribution uncertain) |
| Hertz constant C_H | 89e9 N/m^1.5 | – | CT23 (metro); freight value not found (assumed; enters only through k_H0 and the nonlinear check) |
| Bogie wheelbase | 1.8 m | – | railway-technology.com Y25 ("Wheelbase: 1,800mm"); Tatravagónka Y25 data |
| Bogie pivot pitch / length over buffers | 10.70 m / 15.74 m | – | Rail Cargo Group Eanos fact sheet; Wascosa Eanos 82.5 datasheet |

## Round 2 (full-text checks and missing values)

No page could be fetched in round 2 either (WebFetch DNS failures; proxy 403 for publisher, PMC, DiVA and HAL hosts), so the status of every value stays **snippet**. Changes made:

| Item | Round-2 finding | Action |
|---|---|---|
| c_B = 6740 N s/m (Li et al. 2019) | parameter defined in the paper, value not seen | relabelled **assumed, swept** (3000–12000 N s/m in the sweep) |
| Wheelset modal damping (Chaar 2007) | measured first torsion/bending damping "less than 2%", not "less than 1%" | range widened to 0.1–2%; sweep high end 2% |
| k_p 1017 / 2280 kN/m | found in Dusza (2023) Rail Vehicles, empty/loaded confirmed; not in Dusza et al. (2024) | citation moved; per-axlebox vs per-spring-set unresolved |
| Bižić & Petrović (2021) | venue is Mechanics Transport Communications 19(3), art. 2113 (Sofia), not the Žilina journal; same authors give 1074 kg wheelset mass elsewhere (1350 kg here) | citation corrected; wheelset mass not used directly |
| Axlebox 100 kg (Dusza et al. 2024) | seen in the preprint table (bogie frame 1600 kg, wheelset 1400 kg, axlebox 100 kg) | kept |
| Rail pad 200 MN/m (Thompson et al. 2007) | confirmed in snippet; sleeper mass, ballast stiffness and pad loss factor not found | loss factor stays a swept range |
| Wheelset 998 kg, wheel 304 kg, axle 390 kg (Unirail BA004) | sums consistent | kept |
| Unsprung 1355 kg (RIVAS D5.5; Nielsen et al. 2015) | confirmed in snippet | kept |
| Bearing geometry (Guan, Deng & Wang 2023, Sci. Rep. 13, art. 22680) | z 21, d_m 180.5 mm, l 45 mm, D 23 mm, contact angles 7.75°/10° (printed "mm") | kept; high-speed TRB used as proxy for the freight bearing |
| Eanos layout, Y25 wheelbase | confirmed (Rail Cargo, Wascosa: outer axle base 12.50 m = 10.70 + 1.80 m) | kept |

Second round-2 agent (missing bearing, contact and wagon values), all snippet level:

| Item | Value / range seen | Source (snippet) | Action |
|---|---|---|---|
| Bearing-only vertical stiffness (EMU axle-box bearing) | 4.96e9 N/m | "Dynamic load calculation method of EMU axle box bearing based on vehicle dynamics", J. Mech. Eng. 2023, doi 10.3901/JME.2023.14.179 (authors not seen) | k_B0 sweep extended to 5e9 N/m (`kB0_ext`) |
| Bustos et al. 2025 "7.6e8 N/m total supporting stiffness" | not seen in round 2; rig bogie is a Y21, not a Y25 | Bustos et al. (2025) | dropped as an indication |
| Y25 axlebox bearing type | cylindrical roller bearings WJ/WJP 130×240 in DB freight service | Schaeffler "Axlebox bearings for freight cars"; Novotný & Babka (2025), Current Problems in Rail Vehicles 27:189–194, doi 10.46585/spkv20252667 | health check adds a cylindrical variant (contact angle 0) |
| WJ/WJP 130×240 radial clearance | 130–180 µm (unmounted) | SKF Railway Technical Handbook (DIN 5412-11); Schaeffler TPI 256 | cylindrical variant at 20, 130, 180 µm initial clearance |
| Y25 primary vertical damping (equivalent viscous) | 7 kN s/m empty, 123.3 kN s/m laden | Dusza, Gołofit-Stawińska & Zboiński (2024), Appl. Sci. 14(11) 4545, Table A1 | c_p sourced; sweep range 7e3–1.233e5 N s/m (was 5e3–5e5 assumed) |
| Empty axle load | 5.8–6.6 t (Eanos tare 23.1–26.5 t / 4) | Wascosa Eanos 82.5 (23.1 t); DB Cargo Eanos-x 056 (23.5 t); Greenbrier (24.0 t); VTG (24.5–26 t); Tatravagónka Eanoss (24.6 t); Transwagon (26.5 t) | design keeps 5.5 t (already running); sweep `W_min` 5.8–6.6 t quantifies the effect on the bound |
| Hertz contact stiffness range 1.4–2.3e9 N/m | attribution resolved | Hasan N. (2020), "Hertzian contact stiffness under Eisenmann assumptions", ICTD 2020, ASCE, doi 10.1061/9780784483176.010 | source updated |
| C_H for freight wheels; wheel diametral inertia; freight TBU internal geometry; mounted clearance | not found | – | stay assumed, swept |

Open before submission: full-text checks of all of the above once publisher hosts are reachable.


## Decisions of 2026-10-15 (after the user's full-text check)

**Single vehicle source.** The representative vehicle is a four-axle Eaos/Eanos-type wagon on Y25
bogies on ballasted 60E1/UIC60 track. The vehicle set comes from one source: Dusza, Gołofit-Stawińska &
Zboiński (2024), Appl. Sci. 14(11) 4545, Table A1, **full text verified by the user**. It gives
axlebox 100 kg, wheelset 1400 kg, k_p 1017/2280 kN/m (empty/loaded, per axlebox: Dusza 2023 places the
springs "on each axle box"), c_p 7/123.3 kN s/m, rolling radius 0.46 m, S1002 wheels on UIC60 rail.
Nominals use the empty values (k_p 1.017e6 N/m, c_p 7e3 N s/m; c_p was 1e4 before). Loaded values bound
the sweep.

**Wheelset mass: 998 kg vs 1400 kg.** 998 kg is a vendor's *bare* wheelset: an EN axle (390 kg) and two
920 mm ER7 wheels (304 kg each), with no bearings, axleboxes or attached parts (Unirail BA004,
snippet). The model's bare wheelset, an FE axle of 397 kg plus two 304 kg wheels, is 1005 kg and matches.
Dusza et al.'s 1400 kg is the wheelset body of a multibody model. Such bodies usually include the
bearing inner parts and other journal-mounted items, and the 1400 kg is close to the 1355 kg *unsprung*
mass per wheelset that RIVAS D5.5 gives for a Y25 bogie with 920 mm wheels (snippet). So the two figures
describe different assemblies. The model keeps the bare wheelset and puts the axleboxes (2 × 100 kg) in
separately. That gives an unsprung mass of 1205 kg, so the model leaves out about 150 kg of bearings and
attached parts. One WJ 130×240×80 bearing weighs about 15 kg (supplier listings, snippet), and there are
four per wheelset. The 10% support-mode rule was applied to 1400 kg, adding the 395 kg either on the
wheels or lumped on the journals:

| Wheelset mass | Placement | Symmetric modes with axlebox participation (Hz), share of axlebox energy |
|---|---|---|
| 1005 kg (nominal) | – | 405 (0.40), 504 (0.21) |
| 1400 kg | wheels | 399 (support mode by max share) |
| 1400 kg | journals | 399 (0.26), 497 (0.37) |

The ~400 Hz mode moves by at most 1.5%, so the rule is not triggered. With 200 kg on each journal,
however, the larger axlebox share moves to the 497 Hz mode, so the "support mode" label switches between
two modes 100 Hz apart. 200 kg per journal is far more than the bearings (about 30 kg per journal), so
this placement is an upper bound. The sweep (`wheelset_mass_wheels`, `wheelset_mass_journals`,
1400 and 1526 kg) reports the bound and detection limit for both placements.

**Wheel layout.** The freight runs already use the Y25/Eanos layout (wheelbase 1.80 m, bogie pivot
pitch 10.70 m, length over buffers 15.74 m; `config/track.yaml: layout_freight`). No metro layout is
in use for the freight results.

**Contact stiffness.** k_H0 now comes from Hertz theory (Johnson 1985) for an S1002 wheel with rolling
radius 0.46 m (Dusza, verified) on a UIC60 rail with crown radius 0.30 m (snippet). The wheel's
transverse radius is taken as infinite (conical tread; the S1002 value at the nominal point was not
found). At W0 = 22.5 t (110 kN per wheel) this gives k_H0 = 1.489e9 N/m and C_H = 94.1e9 N/m^1.5. For
wheel transverse radii of +0.5 m to −1.0 m it gives 1.388–1.576e9 N/m
(`results/p4/contact_hertz.json`). This is within the published spread of 1.4–2.3e9 N/m (Hasan 2020,
cross-check only). k_H0 was 1.4e9 N/m before.

**Bearing (health case).** Main case: two single-row cylindrical roller bearings WJ + WJP 130×240×80
per journal (Schaeffler; Novotný & Babka 2025; snippet). Contact angle 0. The roller count (18, swept
15–21) and length (48 mm, swept 40–56) are assumed from the envelope. Initial clearance 130 µm: this is
the lower *unmounted* value of 130–180 µm. The SKF Railway Technical Handbook was not reachable (proxy
refused cdn.skfmediahub.skf.com), so the mounted/operating clearance is not known; it is swept over
0–180 µm. Secondary case: the proxy tapered unit, as before.

**Running headline.** The 5-seed freight headline was launched with k_H0 1.4e9 and c_p 1e4. It is
pinned to that config (`config/snapshots/headline_freight_v1`, `WHEELSET_CONFIG_DIR`) so that no
chunk mixes nominals. Under the 10% rule it is kept. Every other rerun (Fisher bounds, model-form,
drift, sweep, health, exponent bound, inverse-crime check) uses the current config.
