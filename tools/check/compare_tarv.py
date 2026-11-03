"""CAPRI's TARV (data_market_1730defaulta.csv) against capri_data/2017/policy/tariffs.csv (docs/design/TARV_COMPARISON.md).

    python tools/check/compare_tarv.py [OUT.csv]
"""
import re, sys
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'/'build'),str(ROOT/'tools'/'lib')]
from paths import EXPORTS
from build_bilateral_market import MODEL
tv={}
pat=re.compile(r"^'([^']+)'\.'(TARV|TARS)'\.'([A-Z]+)'\.'(2017|CAL)'\s+(Eps|[-\d.Ee+]+)")
for l in open(EXPORTS/'data_market_1730defaulta.csv',errors='ignore'):
    m=pat.match(l)
    if m:
        r,it,p,y,v=m.groups(); tv[(r,it,p,y)]=0.0 if v=='Eps' else float(v)
t=pd.read_csv(ROOT/'capri_data'/'2017'/'policy'/'tariffs.csv',index_col=0)
# model region -> RMTP: same name where it exists
alias={'EU27':'EU','NOR':'NO000000','UK':'UK000000'}
rows=[]
for reg in t.index:
    tp=alias.get(reg,reg)
    for c in t.columns:
        ps=MODEL.get(c,(c,))
        if len(ps)!=1: continue
        k=(tp,'TARV',ps[0],'2017')
        if k in tv:
            rows.append(dict(region=reg,rmtp=tp,commodity=c,model_ave=float(t.at[reg,c]),tarv_2017=tv[k],tarv_cal=tv.get((tp,'TARV',ps[0],'CAL')),tars_2017=tv.get((tp,'TARS',ps[0],'2017'))))
d=pd.DataFrame(rows)
if len(sys.argv) > 1:
    d.to_csv(sys.argv[1], index=False)
print(len(d), d.region.nunique(), 'regions matched of', len(t.index), sorted(set(t.index)-set(d.region)))
d['diff']=d.model_ave-d.tarv_2017
print('MAD model AVE vs TARV 2017 (pp):', round(d['diff'].abs().mean(),2), 'median', round(d['diff'].abs().median(),2))
print('TARV 2017 == CAL share:', round((d.tarv_2017.sub(d.tarv_cal).abs()<1e-9).mean(),3))
print(d[d.region=='EU27'].sort_values('diff',key=abs,ascending=False).head(12).round(2).to_string(index=False))
print(d.groupby('region')['diff'].apply(lambda s:s.abs().mean()).round(1).sort_values().to_string())
