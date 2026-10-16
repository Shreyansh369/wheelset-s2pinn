"""Generator check, part 2: Monte Carlo mean periodogram of the time-domain generator (linear contact) against
the frequency-domain generator for one pass (85 km/h, 14 t, current config, noise-free), 200 realisations each.
Writes results/p4/generator_expper.json.
"""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.utils.results import save_result
from experiments.p1_fe_direct import TRUTH
from experiments.p2_common import setup
from experiments.p2_multiwheel import KMH, FG, models
from src.reference.time_domain_contact import NonlinearContactGenerator
from src.inverse.multipass import generate_pass
sm,thb,rough,_=setup(); mw=models(sm)[0]['4']; th=dict(thb,**TRUTH)
gen=NonlinearContactGenerator(mw,th); V=85*KMH; W=14.0; g=np.ones(rough.n_sub)
Hf=mw.reference_H(dict(th,W=W),V,FG)
R=200
td=[];fdv=[]
for i in range(R):
    p=gen.simulate(rough,g,V,W,th['r0'],200.0,np.random.default_rng(1000+i),contact='linear'); td.append(np.abs(p['c'])**2)
    q=generate_pass(Hf,rough,g,V,th['r0'],200.0,np.random.default_rng(5000+i)); fdv.append(np.abs(q['c'])**2)
f=p['f']; td=np.mean(td,0); fdv=np.mean(fdv,0)
assert np.allclose(f,q['f'])
rows=[]
for lo,hi in ((45,300),(300,380),(380,430),(430,480),(480,550),(550,700)):
    s=(f>=lo)&(f<hi)
    rows.append({"band_hz":[lo,hi],"n_bins":int(s.sum()),"mean_log_ratio_td_fd":float(np.mean(np.log(td[s]/fdv[s]))),
                 "ratio_of_band_power_td_fd":float(td[s].sum()/fdv[s].sum()),"log_ratio_se":float(np.std(np.log(td[s]/fdv[s]))/np.sqrt(s.sum()))})
    print(rows[-1])
save_result("p4/generator_expper",{"realisations":R,"rows":rows},cfg={"pass":"85 km/h, 14 t, 4 wheels, noise-free"},seed=1000)
