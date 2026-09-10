#!/usr/bin/env python3
from __future__ import annotations
from collections import defaultdict
from pathlib import Path
import argparse, json, math, random, statistics

PHASE_COEFF={
"citrus_top":(.72,.24,.04),"aromatic_top":(.56,.34,.10),"spice":(.42,.43,.15),
"green_fruit":(.52,.38,.10),"marine_green":(.45,.45,.10),"air_floral":(.18,.62,.20),
"orris_violet":(.12,.56,.32),"woods_amber":(.04,.34,.62),"resin_incense":(.03,.29,.68),
"sweet_balsamic":(.02,.26,.72),"musk":(.04,.34,.62),"leather":(.02,.28,.70),
"technical":(0,0,0)}
RELEASE={"V":[1.2e-3,5e-4,5e-5,3e-6],"M":[4e-4,5e-4,1.8e-4,2e-5],
"B":[1.2e-4,2.4e-4,3.2e-4,8e-5],"U":[4e-5,1e-4,2.8e-4,2e-4]}
PHASE_TIME={"top":[0,1],"heart":[1,2],"base":[2,3]}
FAMILIES=["citrus_top","aromatic_top","spice","green_fruit","marine_green","air_floral",
"orris_violet","woods_amber","resin_incense","sweet_balsamic","musk","leather"]

def af(row): return row["fraction"] if isinstance(row["fraction"],(int,float)) else .5
def cosine(a,b):
    dot=sum(x*y for x,y in zip(a,b)); na=math.sqrt(sum(x*x for x in a)); nb=math.sqrt(sum(y*y for y in b))
    return dot/(na*nb) if na and nb else 0.0
def phase_vector(rows):
    out=[0.,0.,0.]
    for r in rows:
        basis=r["parts"]*af(r)
        for i,c in enumerate(PHASE_COEFF[r["family"]]): out[i]+=basis*c
    total=sum(out); return [x/total for x in out]
def oav(rows,conc,threshold_mult=1.,release_mult=1.,fraction_mult=None):
    out={}
    for r in rows:
        frac=af(r)*(fraction_mult.get(r["name"],1.) if fraction_mult else 1.)
        mg_l=conc*r["parts"]*frac*1000.
        out[r["name"]]=[mg_l*50*RELEASE[r["volatility"]][t]*release_mult/r["threshold"] for t in range(4)]
    return out
def signatures(spec,rows,tm=1.,rm=1.,fm=None):
    values=oav(rows,spec["concentration"],tm,rm,fm); sums=defaultdict(float); passed=0
    for name,phase in spec["signatures"]:
        score=max(values.get(name,[0,0,0,0])[i] for i in PHASE_TIME[phase])
        sums[phase]+=score; passed+=score>=1
    return passed/len(spec["signatures"]),all(v>=1 for v in sums.values()),dict(sums)
def dominance(spec,rows):
    values=oav(rows,spec["concentration"]); maximum=0.
    for t in range(4):
        total=sum(v[t] for v in values.values())
        if total: maximum=max(maximum,max(v[t]/total for v in values.values()))
    return maximum
def monte_carlo(spec,rows,n=1800,seed=5606):
    rng=random.Random(seed); pv=phase_vector(rows); dom=dominance(spec,rows)
    overall=oav_pass=temporal_pass=0; ts=[]
    for _ in range(n):
        tm=math.exp(rng.gauss(0,.52)); rm=math.exp(rng.gauss(0,.28)); fm={}
        for r in rows:
            sigma=.03 if r["fraction"]==1 else .08 if isinstance(r["fraction"],(int,float)) else .16
            fm[r["name"]]=max(.35,rng.gauss(1,sigma))
        cov,phase_ok,_=signatures(spec,rows,tm,rm,fm); oav_ok=cov>=.65 and phase_ok; oav_pass+=oav_ok
        noisy=[max(0,x*math.exp(rng.gauss(0,.10))) for x in pv]; s=sum(noisy); noisy=[x/s for x in noisy]
        temp=cosine(noisy,spec["expected_phase"]); ts.append(temp); temp_ok=temp>=.90; temporal_pass+=temp_ok
        d=min(1,max(0,dom*math.exp(rng.gauss(0,.12))))
        overall+=oav_ok and temp_ok and d<=.70
    ts.sort()
    return {"simulations":n,"overall_pass_probability":overall/n,"oav_pass_probability":oav_pass/n,
    "temporal_pass_probability":temporal_pass/n,"temporal_similarity_mean":statistics.mean(ts),
    "temporal_similarity_p05":ts[int(.05*n)],"temporal_similarity_p95":ts[int(.95*n)-1]}

def main():
    ap=argparse.ArgumentParser(description="Perfume Verification Engine V2")
    ap.add_argument("state_json",type=Path); ap.add_argument("--output",type=Path,default=Path("engine_v2_output.json"))
    ap.add_argument("--simulations",type=int,default=1800); args=ap.parse_args()
    data=json.loads(args.state_json.read_text(encoding="utf-8")); results=[]
    for f in data["formulas"]:
        spec=f["spec"]; rows=f["rows"]; cov,phase_ok,sums=signatures(spec,rows)
        mc=monte_carlo(spec,rows,args.simulations,5606+len(results))
        results.append({"code":spec["code"],"target":spec["name"],"marker_coverage":cov,
        "phase_oav_pass":phase_ok,"phase_oav_sums":sums,"phase_similarity":cosine(phase_vector(rows),spec["expected_phase"]),
        "max_oav_share":dominance(spec,rows),"monte_carlo":mc,
        "boundary":"Computational screen only. No measured-headspace or sensory-equivalence claim."})
    args.output.write_text(json.dumps({"engine":"Verification Engine V2","results":results},indent=2),encoding="utf-8")
    print(f"Wrote {len(results)} profile results to {args.output}")
if __name__=="__main__": main()
