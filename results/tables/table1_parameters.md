# Table 1. Representative freight wagon and track: model parameters and sources

| Group | Parameter | Value | Range | Unit | Source |
|---|---|---|---|---|---|
| Material | E | 2.1e+11 | – | Pa | doc §16 (standard steel) |
| Material | nu | 0.3 | – | - | doc §16 |
| Material | rho | 7850 | – | kg/m^3 | doc §16 |
| Axle | length | 2.18 | 2.18–2.188 | m | [snippet] BA004 freight wheelset (Y25), total axle length 2180 mm (railwayspare-parts.com listing); 2187.6 mm Type D axle (same vendor) |
| Axle | sections [outer ξ, d] | [[0.64,0.173],[0.86,0.2],[0.9,0.16],[1.09,0.13]] | – | m | diameters [snippet]: body 173 mm, wheel seat 200 mm, journal 130 mm (BA004 listings; Unirail BA004, EN 13261 130x191 mm); dust-guard collar 160 mm and section boundaries assumed, swept |
| Axle | wheel_xi | 0.75 | – | m | [snippet] 2s = 1500 mm between nominal rolling circles (Bizic & Petrovic 2021, Mechanics Transport Communications 19(3), art. 2113) |
| Axle | journal_xi | 1 | – | m | [snippet] 2b = 2000 mm between axle-box centres (Bizic & Petrovic 2021) |
| Axle | n_elements | 32 | – | - | brief: 20-40 elements; convergence checked at 20/30/40 |
| Axle | damping_zeta | 0.01 | 0.001–0.02 | - | [snippet] measured damping ratios of the first torsion and first and second bending modes below 2% (Chaar 2007, KTH doctoral thesis TRITA AVE 2007:17, Table 2-1); 0.1-1.0% (IPME paper, citation incomplete); swept |
| Axle | damping_fref | 96 | 96–115 | Hz | [snippet] first wheelset bending mode of a freight wagon 96 Hz (Sci. Rep. 2025, s41598-025-15781-4); 115 Hz (Mu et al. 2021, Shock Vib. 4677851) |
| Wheel | mass | 304 | – | kg | [snippet] 920 mm ER7 wheel, nominal weight 304 kg (Unirail BA004 and BA 092 wheelset pages) |
| Wheel | diametral_inertia | 20 | 10–30 | kg m^2 | assumed, swept (single-wheel inertia not found; disc estimate m r^2/4) |
| Wheel | r0 | 0.46 | 0.42–0.46 | m | [snippet] new wheel 920 mm (Y25 bogie data, railway-technology.com; Bizic & Petrovic 2021), worn limit 840 mm (Unirail) |
| Support | kB0 | 1e+09 | 5e+08–5e+09 | N/m | assumed, swept (effective support stiffness of a freight axlebox not found; indications [snippet]: equivalent vertical stiffness of an EMU axle-box bearing 4.96e9 N/m, bearing only (J. Mech. Eng. 2023, 10.3901/JME.2023.14.179); adapter-pad vertical stiffness 8.8e8-5.3e9 N/m, three-piece-truck patent US 9,580,087) |
| Support | cB | 6740 | 3000–1.2e+04 | N s/m | assumed, swept (round-1 snippet attributed 6740 N s/m to Li et al. 2019, Adv. Mech. Eng. 11(4), 10.1177/1687814019840503; round 2 found the parameter defined there but not the value) |
| Support | load_exponent | 0.1 | – | - | doc Eq. (12): Q ~ delta^(10/9) gives k ~ Q^(1/10) |
| Bearing (health check) | rollers_per_row | 21 | 17–23 | - | [snippet] 130 mm-bore double-row TRB: z = 21 (Guan et al. 2023, Sci. Rep. 13; Liu & Du 2020, IJAV 25(4)); 23 for the 150 mm 353130B freight unit (Sun et al. 2026); proxy, freight 130 mm unit not found |
| Bearing (health check) | roller_length | 45 | – | mm | [snippet] effective length 45 mm (Guan et al. 2023), proxy |
| Bearing (health check) | roller_diameter | 23 | 21.4–26.5 | mm | [snippet] 23 mm (Guan et al. 2023; Liu & Du 2020); 21.384 mm (353130B); 26.5 mm (Zhao et al. 2024) |
| Bearing (health check) | pitch_diameter | 180.5 | – | mm | [snippet] 180.5 mm (Guan et al. 2023; Liu & Du 2020), proxy |
| Bearing (health check) | contact_angle | 10 | – | deg | [snippet] outer-race contact angle 10 deg (Liu & Du 2020; Zhao et al. 2024) |
| Bearing (health check) | clearance_d0 | 20 | 0–50 | um | assumed, swept (mounted axial endplay 0.025-0.381 mm [snippet], Timken AP manual; conversion to radial clearance not sourced) |
| Axlebox | mass | 100 | 100–158.4 | kg | [snippet] axlebox 100 kg in a Y25 multibody model (Dusza et al. 2024, Appl. Sci. 14(11) 4545); 158.42 kg (Bustos et al. 2025, Y21 bogie rig model) |
| Primary | kp | 1.017e+06 | 9.8e+05–2.6e+06 | N/m | [snippet] Y25 primary vertical stiffness 1017 kN/m empty / 2280 kN/m loaded (Dusza 2023, Rail Vehicles 2023(3-4) 13-24, 10.53502/RAIL-175725; per axlebox or per spring set not resolved); spring-set rate 980 (tare) to 2600 N/mm (laden), EP 1484228 A1 |
| Primary | cp | 1e+04 | 7000–1.233e+05 | N s/m | [snippet] Y25 primary equivalent vertical damping 7 kN s/m (empty) and 123.3 kN s/m (laden), identified from measured car responses (Dusza, Golofit-Stawinska & Zboinski 2024, Appl. Sci. 14(11) 4545, Table A1; per axlebox not stated); swept |
| Payload | W_min | 5.5 | 5.8–6.6 | t | design value 5.5 t; [snippet] Eanos tare 23.1 t (Wascosa), 23.5 t (DB Cargo), 24.0 t (Greenbrier), 24.5-26.5 t (VTG, Tatravagonka, Transwagon), i.e. empty axle load 5.8-6.6 t; effect of 5.8-6.6 t on the bound in results/p4/sweep.json |
| Payload | W_max | 22.5 | – | t | [snippet] Y25 bogie axle load 22.5 t (railway-technology.com, Y25 bogie) |
| Payload | W0 | 22.5 | – | t | reference load for kB0 (loaded) |
| Rail 60E1 | A | 0.00767 | – | m^2 | [snippet] 76.70 cm^2, mass 60.21 kg/m (ArcelorMittal 60E1 datasheet, EN 13674-1; Valente; British Steel rail profiles datasheet) |
| Rail 60E1 | I | 3.038e-05 | – | m^4 | [snippet] I_xx 3038.3 cm^4 (British Steel and ArcelorMittal datasheets, EN 13674-1) |
| Rail 60E1 | kappa | 0.4 | 0.34–0.4 | - | [snippet] rail shear coefficient 0.4 (TU Delft thesis, rail close to UIC54); 0.393 for UIC60 (attribution weak); 0.34 BS113A (CT23 Table 1) |
| Track (ballasted) | pad_stiffness | 2e+08 | 8e+07–8e+08 | N/m | [snippet] typical UIC60 ballasted track, rail pad 200 MN/m per pad (Thompson, Jones, Waters & Farrington 2007, Appl. Acoust. 68(1) 43-57); 80 kN/mm (EUROBOLT optimal track, Nova chapter); 800/120 MN/m stiff/soft (Thompson et al., attribution weak) |
| Track (ballasted) | sleeper_spacing | 0.6 | 0.6–0.65 | m | [snippet] 0.6 m (EUROBOLT optimal track); 0.65 m (CT23 Table 1; Thompson et al.) |
| Track (ballasted) | kf | 3.333e+08 | 1.23e+08–1.333e+09 | N/m^2 | derived: pad stiffness / sleeper spacing (pad modulus, PWI Guide to Track Stiffness definition) from the sourced ranges above; ballast compliance in series not modelled |
| Track (ballasted) | eta_f | 0.2 | 0.1–0.25 | - | [snippet] rail pad loss factor 0.16 (Thompson et al. 2007 table), 0.25 (rolling-noise models), about 0.1 (EVA) to 0.2 (natural rubber) pads |
| Contact | kH0 | 1.4e+09 | 1.4e+09–2.3e+09 | N/m | [snippet] linearised Hertzian contact stiffness spread 1400-2300 kN/mm across authors (Hasan N. 2020, Hertzian contact stiffness under Eisenmann assumptions, Int. Conf. Transportation and Development, ASCE, 10.1061/9780784483176.010); nominal at the low end (C_H above at 110 kN) |
| Contact | C_H | 8.9e+10 | – | N/m^1.5 | CT23 Sec. 5.1.2 citing Sanchis et al. (metro wheel/rail radii); freight value not found: assumed, swept through kH0 |
| Layout | wheel positions | [0.0,1.8,10.7,12.5,15.74,17.54,26.44,28.24] | – | m | derived from [snippet] Y25 wheelbase 1800 mm (railway-technology.com; Tatravagonka Y25 data) and Eanos bogie pivot pitch 10.70 m, length over buffers 15.74 m (Rail Cargo Group; Wascosa datasheets): overhang (15.74 - 12.5)/2 per wagon end |


6 of 38 entries were not found in the literature (marked 'assumed, swept'); their effect is in Table 15. [snippet] = value seen in search results; the full-text status of each source is in docs/parameter_sources.md.

Source: `config/params.yaml`, `config/track.yaml`
