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
| Axle-box centre distance 2b | 2000 mm | – | Bižić M., Petrović D. (2021), "Analytical calculation of strength of freight wagon axle in accordance with European standards", Communications – Scientific Letters of the University of Žilina 19(3) ("2b=2000 mm") |
| Rolling-circle distance 2s | 1500 mm | – | Bižić & Petrović (2021) ("2s=1500 mm") |
| Wheel diameter (new / worn) | 920 mm (r0 = 0.46 m) | 840–920 mm | Bižić & Petrović (2021); Unirail BA004 ("Minimal repair diameter: Ø840mm"); railway-technology.com Y25 bogie |
| Wheel mass | 304 kg | – | Unirail BA004 and BA 092 pages ("Nominal weight: 304kg. Material: ER7") |
| Axle mass | (from FE geometry) | 390 kg (EN axle) | Unirail BA004 |
| Wheelset mass | – | 998–1526 kg | Unirail BA004 998 kg; Bosso, Magelli & Zampieri (2023) Appl. Sci. 13(3) 1318 1080 kg (Y25L, 22.5 t); Dusza (2023) Rail Vehicles 1400 kg; Bižić & Petrović (2021) 1350 kg; others |
| Wheel diametral inertia | 20 kg m² | 10–30 swept | assumed, swept (single-wheel inertia not found; wheelset roll inertia 656–903 kg m² seen) |
| Wheelset modal damping | 1% | 0.1–1% | Chaar N. (2007), KTH doctoral thesis TRITA AVE 2007:17 ("damping ratio for the first five eigenmodes is less than 1%", locomotive wheelset); IPME paper (citation incomplete) "0.1 to 1.0 %" |
| First bending frequency (damping reference) | 96 Hz | 96–115 Hz | Sci. Rep. (2025) s41598-025-15781-4 ("first-order vibration modal frequency of the wheelset (96 Hz)"); Mu et al. (2021) Shock Vib. 4677851 (115 Hz) |
| Unsprung mass per wheelset | (model: axle + wheels + axleboxes) | 1355 kg (Y25, 920 mm), 1610 kg (disc brakes) | RIVAS D5.5 (2013); Nielsen et al. (2015) IJRT 3(1) 17–39 |
| Unsprung-mass uncertainty (1σ) | 4% | – | SKF Evolution, "New axlebox concept for heavy loads" ("around 20 kg per axlebox ... unsprung weight of the wheelset by around 4 %") |

## Axlebox, bearing and suspension

| Parameter | Used | Range seen | Source (snippet) |
|---|---|---|---|
| Axlebox mass | 100 kg | 100–158.4 kg | Dusza, Gołofit-Stawińska, Zboiński (2024), Appl. Sci. 14(11) 4545 (Y25 model: axlebox 100 kg); Bustos, Rubio, Castejón, García-Prada (2025), Adv. Mech. Eng. 17(9) ("Axle box mass 158.42 kg") |
| Effective support stiffness k_B0 | 1.0e9 N/m | 0.5–3e9 swept | **assumed, swept**. Indications: "total supporting stiffness of 7.6·10^8 N/m" (Bustos et al. 2025, meaning unclear); adapter pad ≥ 5e6 lb/in (≥ 8.8e8 N/m) to 3e7 lb/in (5.3e9 N/m), US 9,580,087 (three-piece truck design target) |
| Bearing damping c_B | 6740 N s/m | – | Li T. et al. (2019), Adv. Mech. Eng. 11(4), doi 10.1177/1687814019840503 ("Vertical damping coefficient 6740 N s/m") |
| Primary vertical stiffness k_p | 1.017e6 N/m | 0.98–2.6e6 N/m | Dusza et al. (2024) ("k_zz 1017 and 2280 kN/m", empty/laden order not confirmed); EP 1484228 A1 (Y25 spring set "980N/mm tare and 2600N/mm laden") |
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

*(filled in when the second round reports)*
