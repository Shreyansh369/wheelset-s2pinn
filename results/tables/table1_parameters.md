# Table 1. Representative freight wagon and track: model parameters and sources

| Group | Parameter | Value | Range | Unit | Source |
|---|---|---|---|---|---|
| Material | E | 2.1e+11 | – | Pa | doc §16 (standard steel) |
| Material | nu | 0.3 | – | - | doc §16 |
| Material | rho | 7850 | – | kg/m^3 | doc §16 |
| Axle | length | 2.18 | 2.18–2.188 | m | verified (fetch 19 Oct 2026): axle length 2180 mm (Interpipe, Railway axles, BA 002/BA 302, EN 13261); upper end 2187.6 mm: Type D axle, vendor listing (unverified search result) |
| Axle | sections [outer ξ, d] | [[0.64,0.173],[0.86,0.2],[0.9,0.16],[1.09,0.13]] | – | m | diameters verified (fetch 19 Oct 2026): body 173 mm (Interpipe, Railway axles, BA 002/BA 302, EN 13261); wheel seat 200 mm = BA004 wheel hub bore (vendor listing, railwayspare-parts.com); journal 130 mm (Unirail, Wheelset type BA004, EN 13261 130x191 mm); dust-guard collar 160 mm and section boundaries assumed, swept |
| Axle | wheel_xi | 0.75 | – | m | verified (fetch 19 Oct 2026): 2s = 1500 mm between nominal rolling circles (Bizic & Petrovic 2021, Mechanics Transport Communications 19(3), art. 2113; Bizic & Petrovic 2024, Acta Polytech. Hung. 21(1) 153-166) |
| Axle | journal_xi | 1 | – | m | verified (fetch 19 Oct 2026): 2b = 2000 mm between axle-box cases (as defined in the source) (Bizic & Petrovic 2021; 2024) |
| Axle | n_elements | 32 | – | - | brief: 20-40 elements; convergence checked at 20/30/40 |
| Axle | damping_zeta | 0.01 | 0.001–0.02 | - | verified (fetch 19 Oct 2026): measured damping ratios of the first torsion and first and second bending modes less than 2% (Chaar 2007, KTH doctoral thesis TRITA AVE 2007:17, section 2.1, p. 8); 0.1-1.0% (Jin 2016, Proc. IMechE F 230(3) 643-661, doi 10.1177/0954409714554964, as reported by Ahmedov & Mirsaidov 2023, Mater. Phys. Mech. 51(2), doi 10.18149/MPM.5122023_4); swept |
| Axle | damping_fref | 96 | 96–115 | Hz | verified (fetch 19 Oct 2026): first wheelset bending mode 96 Hz (Han, Li, Zhang & Zhang 2025, Sci. Rep. 15, 33484, doi 10.1038/s41598-025-15781-4; C70 wagon, K6 bogies); 96 Hz; swept 96-115 |
| Wheel | mass | 304 | – | kg | verified (fetch 19 Oct 2026): ER7 wheel 920 mm (840 mm worn), 304 kg; axle 130x191 mm EN 13261, axle 390 kg, wheelset 998 kg (Unirail, Wheelset type BA004 datasheet, unirail.bg) |
| Wheel | diametral_inertia | 20 | 10–30 | kg m^2 | assumed, swept (single-wheel inertia not found; disc estimate m r^2/4) |
| Wheel | r0 | 0.46 | 0.42–0.46 | m | full text verified: rolling radius 0.46 m, S1002 wheels on UIC60 rail (Dusza, Golofit-Stawinska & Zboinski 2024, Appl. Sci. 14(11) 4545, Table A1); worn limit 840 mm diameter, verified (fetch 19 Oct 2026) (Unirail, Wheelset type BA004 datasheet) |
| Support | kB0 | 1e+09 | 5e+08–5e+09 | N/m | assumed, swept (effective support stiffness of a freight axlebox not found) |
| Support | cB | 6740 | 3000–1.2e+04 | N s/m | verified (fetch 19 Oct 2026): vertical damping of the axlebox bearing 6740 N s/m (Li, Sun, Meng, Huo, Dong & Wang 2019, Adv. Mech. Eng. 11(4), doi 10.1177/1687814019840503, Table 3; CHR380 EMU axlebox bearing, no freight value found); swept |
| Support | load_exponent | 0.1 | – | - | doc Eq. (12): Q ~ delta^(10/9) gives k ~ Q^(1/10) |
| Bearing (health check) | rollers_per_row | 18 | 15–21 | - | assumed from the envelope (pitch circle pi x 185 mm / ~1.15 x 27.5 mm roller pitch), swept |
| Bearing (health check) | roller_length | 48 | 40–56 | mm | assumed, ~0.6 x 80 mm bearing width, swept |
| Bearing (health check) | roller_diameter | 27.5 | – | mm | assumed, (240 - 130)/4 mm; does not enter the line-contact law |
| Bearing (health check) | pitch_diameter | 185 | – | mm | envelope: (130 + 240)/2 mm of the WJ/WJP 130x240 bearings on Y25 (Schaeffler WL 07519, verified (fetch 19 Oct 2026)) |
| Bearing (health check) | contact_angle | 0 | – | deg | cylindrical roller bearing |
| Bearing (health check) | clearance_d0 | 130 | 0–180 | um | verified (fetch 19 Oct 2026): radial clearance of WJ/WJP 130x240 P before mounting 130-180 um (SKF Railway Technical Handbook Vol. 1, ch. 4, p. 89, extract, (c) SKF 2012); mounted/operating clearance not found: nominal = lower unmounted value, swept 0-180 um |
| Axlebox | mass | 100 | 100–158.4 | kg | full text verified: axlebox 100 kg (Dusza et al. 2024, Table A1); indication: SKF Y25 axlebox housing 80 kg (SKF Evolution, 26 Sep 2022); upper sweep end 158.4 kg assumed (+58%) |
| Primary | kp | 1.017e+06 | 1.017e+06–2.28e+06 | N/m | full text verified: Y25 primary vertical stiffness 1017 kN/m empty / 2280 kN/m loaded per axlebox (Dusza et al. 2024, Table A1; springs on each axle box, Dusza 2023); nominal = empty value |
| Primary | cp | 7000 | 7000–1.233e+05 | N s/m | full text verified: Y25 primary equivalent vertical damping 7 kN s/m empty / 123.3 kN s/m laden (Dusza et al. 2024, Table A1); nominal = empty value, paired with kp |
| Payload | W_min | 5.5 | 5.8–6.6 | t | design value 5.5 t; verified (fetch 19 Oct 2026): Eanos tare 23,100 kg +-2% (Wascosa, Eanos datasheet), 22.6-25.3 t (Rail Cargo Group, Eanos fact sheet), i.e. empty axle load 5.65-6.3 t; swept 5.6-6.6 t in results/p4/sweep.json (range field kept at 5.8-6.6 t: values-v2 hash) |
| Payload | W_max | 22.5 | – | t | verified (fetch 19 Oct 2026): Y25 axle load 22.5 t (Tatravagonka, Y25Lssi(f)-D data page; Wascosa, Eanos datasheet) |
| Payload | W0 | 22.5 | – | t | reference load for kB0 (loaded) |
| Rail 60E1 | A | 0.00767 | – | m^2 | verified (fetch 19 Oct 2026): 76.70 cm^2 (TSTG Schienen Technik, rail profile catalogue, 60E1; Knuth et al. 2025, Table 1: 7.7e-3 m^2) |
| Rail 60E1 | I | 3.038e-05 | – | m^4 | verified (fetch 19 Oct 2026): I_xx 3038.3 cm^4 (British Steel, Rail profiles and grades, EN 13674-1) |
| Rail 60E1 | kappa | 0.4 | 0.34–0.4 | - | verified (fetch 19 Oct 2026): rail shear coefficient 0.393, UIC60 vertical (Knuth, Squicciarini & Thompson 2025, JSV 618B 119323, doi 10.1016/j.jsv.2025.119323, Table 1, from Kostovasilis et al.); 0.4 (de Man 2000, HERON 45(1), 133-FB rail, close to UIC54); 0.34 (Grassie et al., via de Man 2000) |
| Track (ballasted) | pad_stiffness | 2e+08 | 8e+07–8e+08 | N/m | verified (fetch 19 Oct 2026): nominal 200 MN/m per pad within the published 105-800 MN/m (Knuth et al. 2025, Table 2: 105 MN/m; Thompson, Zhang, Ntotsios & Squicciarini, accepted manuscript, Southampton eprint 436918, Table 1: 800/120 MN/m); swept 80-800 MN/m |
| Track (ballasted) | sleeper_spacing | 0.6 | 0.6–0.65 | m | verified (fetch 19 Oct 2026): 0.6 m (Sanudo et al. 2022, Infrastructures 7(6) 83, doi 10.3390/infrastructures7060083); 0.65 m (Thompson et al., Southampton eprint 436918, Table 1) |
| Track (ballasted) | kf | 3.333e+08 | 1.23e+08–1.333e+09 | N/m^2 | derived: pad stiffness / sleeper spacing (pad modulus, PWI Guide to Track Stiffness definition) from the sourced ranges above; ballast compliance in series not modelled |
| Track (ballasted) | eta_f | 0.2 | 0.1–0.25 | - | verified (fetch 19 Oct 2026): rail pad loss factor 0.25 / 0.2 (Thompson et al., Southampton eprint 436918, Table 1), 0.15 (Knuth et al. 2025, Table 2), 0.1-0.3 (Jones & Edwards, Internoise 1996) |
| Contact | kH0 | 1.489e+09 | 1.388e+09–2.3e+09 | N/m | Hertz theory at W0 = 22.5 t (F0 = 110 kN), results/p4/contact_hertz.json: 1.388-1.576 GN/m Hertz (S1002 transverse radius +0.5 m to -1.0 m); upper sweep end 2.3 GN/m assumed |
| Contact | C_H | 9.413e+10 | – | N/m^1.5 | Hertz theory (Johnson 1985): S1002 wheel, rolling radius 0.46 m (Dusza et al. 2024, full text verified), on UIC60 rail, crown radius 0.30 m (R300 head radius of the 60E1 profile, EN 13674-1; drawing in the TSTG rail profile catalogue, verified (fetch 19 Oct 2026)); wheel transverse radius infinite (assumed); results/p4/contact_hertz.json |
| Layout | wheel positions | [0.0,1.8,10.7,12.5,15.74,17.54,26.44,28.24] | – | m | derived from Y25 wheelbase 1800 mm (Tatravagonka, Y25Lssi(f)-D data page) and Eanos bogie pivot pitch 10.70 m, length over buffers 15.74 m (Rail Cargo Group, Eanos fact sheet; Wascosa: length over buffers 15,740 mm, outer axle base 12,500 mm), verified (fetch 19 Oct 2026): overhang (15.74 - 12.5)/2 per wagon end |


9 of 38 entries were not found in the literature (marked 'assumed, swept'); their effect is in Table 15. 'Verified (fetch 19 Oct 2026)' = checked against the source document; quotes, URLs and the status of each source are in docs/table1_sources_candidates.md and docs/parameter_sources.md.

Source: `config/params.yaml`, `config/track.yaml`
