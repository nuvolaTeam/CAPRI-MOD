"""Nitrogen-target abatement by channel for one region (diagnostic, Sprint 2).

Solves the region at base prices with only the nitrogen-balance target, at a series of cuts, and splits the
surplus reduction into herds, crops (area) and the rest (technologies, yields), with the nitrogen shadow price.
Usage: python tools/diag_n_abatement.py FRH0 0.1,0.3,0.57
"""
import sys, warnings, json; warnings.filterwarnings("ignore"); sys.path.insert(0,'.')
import pandas as pd, numpy as np
from capri_mod.model import CAPRIModel
from capri_mod.policy.greendeal import greendeal_scenario
from capri_mod.supply.supply_module import SupplyModule
from capri_mod.data.definitions import CROPS, ANIMALS
reg=sys.argv[1]; cuts=[float(x) for x in sys.argv[2].split(',')]
m=CAPRIModel(data_dir='capri_data',verbose=False)
sm=m.supply_module
env=None
rows=[]
base=None
for cut in cuts:
    SupplyModule.JRC_CAPPED_CUT=cut
    sm._jrc_capped_cache={reg}
    r=m.run(custom_scenario=greendeal_scenario(lndscpTarg=0,orgTarg=0,pestRedu=0), regions=[reg], max_outer_iter=1, run_environmental=False)
    res=r['supply'][reg]
    acts=res.activities
    if env is None:
        env=sm._env_for_surplus
        mdl=sm._models[reg]; x0=mdl._base_levels()
        y=m.data['yields'].loc[reg]
        unit={a:env.compute_nitrogen_balance({a:1.0},y,reg)['n_surplus'] for a in mdl.acts}
        S0=sum(unit[a]*float(x0.get(a,0)) for a in mdl.acts)
    lam=float(res.shadow_prices.get('N_balance',0.0))
    d={a:float(acts.get(a,0))-float(x0.get(a,0)) for a in mdl.acts}
    herd=sum(unit[a]*d[a] for a in ANIMALS if a in d); crop=sum(unit[a]*d[a] for a in CROPS if a in d)
    rows.append(dict(cut=cut,lam=round(lam,2),S0=round(S0),herd_kg=round(herd),crop_kg=round(crop),
                     other_kg=round(-cut*S0-herd-crop),
                     **{a:round(d[a]/max(float(x0.get(a,0)),1e-9)*100,1) for a in ['DCOW','BULL','BCOW','PIGS','LAYS','BROI','SHGP','GRAS','SWHE','CORN','MAIF','SETA']},
                     land=round(sum(float(acts.get(c,0)) for c in CROPS)/sum(float(x0.get(c,0)) for c in CROPS)*100-100,1),
                     techs=json.dumps({k:round(v,2) for k,v in (getattr(res,'fert_tech_shares',{}) or {}).items()})))
    print(rows[-1], flush=True)
pd.DataFrame(rows).to_csv(f'n_abatement_{reg}.csv',index=False)
