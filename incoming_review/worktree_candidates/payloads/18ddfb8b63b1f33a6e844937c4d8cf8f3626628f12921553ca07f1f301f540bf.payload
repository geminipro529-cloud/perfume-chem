
#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, hashlib, itertools, json
from collections import defaultdict
from pathlib import Path
import numpy as np

PHASE_WINDOWS={"top":(0,1),"heart":(1,2),"base":(2,3)}
PHASE_COEFF={
"citrus_top":(.72,.24,.04),"aromatic_top":(.56,.34,.10),"spice":(.42,.43,.15),
"green_fruit":(.52,.38,.10),"marine_green":(.45,.45,.10),"air_floral":(.18,.62,.20),
"orris_violet":(.12,.56,.32),"woods_amber":(.04,.34,.62),"resin_incense":(.03,.29,.68),
"sweet_balsamic":(.02,.26,.72),"musk":(.04,.34,.62),"leather":(.02,.28,.70),"technical":(0,0,0)}

def cosine(a,b):
    a=np.asarray(a,float); b=np.asarray(b,float); d=np.linalg.norm(a)*np.linalg.norm(b)
    return float(np.dot(a,b)/d) if d else 0.0

def evidence_sigma(e):
    e=str(e or '').upper()
    if e.startswith('MEASURED'): return .20
    if 'QSPR' in e or 'MODEL' in e: return .48
    if 'NATURAL' in e: return .60
    if 'PRODUCT' in e or 'ACCORD' in e: return .72
    return .58

def stock_sigma(r):
    f=r.get('fraction'); s=str(r.get('stock','')).lower()
    if f is None or 'product basis' in s: return .20
    if isinstance(f,(int,float)) and 0<f<1: return .10
    if 'label-lock' in s or 'verify' in s: return .14
    return .06

def matrix_sigma(m):
    return {'hydroalcoholic':.30,'aerosol':.42,'high_concentrate':.40,
            'aqueous_emulsion':.55,'infusion':.55,'extrait':.45}.get(m,.42)

def arrays(p):
    rows=p['rows']; names=[r['name'] for r in rows]
    parts=np.array([float(r['parts']) for r in rows])
    frac=np.array([float(r['fraction']) if isinstance(r.get('fraction'),(int,float)) else .5 for r in rows])
    th=np.array([max(float(r.get('threshold',r.get('threshold_center',1))),1e-12) for r in rows])
    air=np.array([r.get('air_center',[0,0,0,0]) for r in rows],float)
    ph=np.array([PHASE_COEFF[r['family']] for r in rows],float)
    idx={n:i for i,n in enumerate(names)}
    sig=[]
    for m in p.get('signature',[]):
        if m['marker'] not in idx: raise ValueError(f"Missing marker {m['marker']} in {p['target']['code']}")
        sig.append((idx[m['marker']],m['phase'],m['marker']))
    return dict(rows=rows,names=names,parts=parts,frac=frac,th=th,air=air,ph=ph,
                thsig=np.array([evidence_sigma(r.get('threshold_evidence')) for r in rows]),
                dsig=np.array([stock_sigma(r) for r in rows]),sig=sig)

def deterministic(p,a,parts=None):
    x=a['parts'].copy() if parts is None else np.asarray(parts,float)
    x=x/x.sum()*1000; scale=np.nan_to_num(x/a['parts']); air=a['air']*scale[:,None]; coav=air/a['th'][:,None]
    mark=[]; sums=defaultdict(float)
    for i,phase,_ in a['sig']:
        v=float(np.max(coav[i,list(PHASE_WINDOWS[phase])]))
        mark.append(v>=1); sums[phase]+=v
    center=float(np.mean(mark)) if mark else 0; phasepass=all(v>=1 for v in sums.values())
    at=air.sum(0); shape=at/at.sum() if at.sum() else np.zeros(4)
    rel=cosine(shape,p['target']['expected_release'])
    weighted=x*a['frac']; raw=weighted@a['ph']; ps=raw/raw.sum() if raw.sum() else np.zeros(3)
    phsim=cosine(ps,p['target']['expected_phase']); temporal=.6*rel+.4*phsim
    maxshare=0
    for t in range(4):
        total=float(coav[:,t].sum())
        if total: maxshare=max(maxshare,float(coav[:,t].max()/total))
    robust=float(np.mean([min(1,v/3) for v in sums.values()])) if sums else 0
    identity=.33*center+.23*robust+.29*temporal+.15*max(0,1-maxshare)
    hard=center>=.65 and phasepass and temporal>=.70 and maxshare<=.70
    return dict(center_coverage=center,phase_pass=phasepass,temporal_similarity=temporal,
                max_oav_share=maxshare,identity_score=identity,hard_pass=hard)

def monte_carlo(p,n,seed):
    a=arrays(p); rng=np.random.default_rng(seed); N=len(a['names'])
    tm=rng.lognormal(-.5*a['thsig']**2,a['thsig'],size=(n,N))
    dm=rng.lognormal(-.5*a['dsig']**2,a['dsig'],size=(n,N))
    s=matrix_sigma(p['target'].get('matrix',''))
    pr=rng.lognormal(-.5*s*s,s,size=(n,1,1))
    tr=rng.lognormal(-.5*(s*.45)**2,s*.45,size=(n,1,4))
    mr=rng.lognormal(-.5*(s*.30)**2,s*.30,size=(n,N,1))
    air=a['air'][None,:,:]*dm[:,:,None]*pr*tr*mr
    coav=air/(a['th'][None,:,None]*tm[:,:,None])
    marker=[]; phase_sums={}
    for i,phase,_ in a['sig']:
        vals=np.max(coav[:,i,list(PHASE_WINDOWS[phase])],axis=1)
        marker.append(vals>=1); phase_sums.setdefault(phase,np.zeros(n)); phase_sums[phase]+=vals
    center=np.stack(marker,1).mean(1); phasepass=np.ones(n,bool)
    for vals in phase_sums.values(): phasepass &= vals>=1
    at=air.sum(1); shape=at/np.clip(at.sum(1,keepdims=True),1e-12,None)
    er=np.array(p['target']['expected_release']); rel=np.sum(shape*er,1)/(np.linalg.norm(shape,axis=1)*np.linalg.norm(er))
    up=a['parts'][None,:]*dm; raw=(up*a['frac'][None,:])@a['ph']; ps=raw/np.clip(raw.sum(1,keepdims=True),1e-12,None)
    ep=np.array(p['target']['expected_phase']); ph=np.sum(ps*ep,1)/(np.linalg.norm(ps,axis=1)*np.linalg.norm(ep))
    temporal=.6*rel+.4*ph
    maxshare=np.zeros(n)
    for t in range(4):
        total=coav[:,:,t].sum(1); maxshare=np.maximum(maxshare,coav[:,:,t].max(1)/np.clip(total,1e-12,None))
    hard=(center>=.65)&phasepass&(temporal>=.70)&(maxshare<=.70)
    return dict(n_simulations=n,pass_probability=float(hard.mean()),
                marker_coverage_probability=float((center>=.65).mean()),
                phase_pass_probability=float(phasepass.mean()),
                temporal_pass_probability=float((temporal>=.70).mean()),
                dominance_pass_probability=float((maxshare<=.70).mean()),
                temporal_median=float(np.median(temporal)),
                temporal_p05=float(np.quantile(temporal,.05)),
                temporal_p95=float(np.quantile(temporal,.95)),
                max_share_median=float(np.median(maxshare)),
                max_share_p95=float(np.quantile(maxshare,.95)),
                center_coverage_median=float(np.median(center)))

def ablation(p):
    a=arrays(p); base=deterministic(p,a); out=[]
    for i,n in enumerate(a['names']):
        x=a['parts'].copy(); x[i]=0; m=deterministic(p,a,x); impact=base['identity_score']-m['identity_score']
        label='IDENTITY CRITICAL' if impact>=.08 or (base['hard_pass'] and not m['hard_pass']) else 'STRUCTURALLY IMPORTANT' if impact>=.04 else 'TEXTURAL SUPPORT' if impact>=.015 else 'DECORATIVE / REMOVE CANDIDATE'
        out.append(dict(material=n,parts_per_1000=float(a['parts'][i]),identity_impact=float(impact),
                        ablated_identity_score=m['identity_score'],ablated_hard_pass=m['hard_pass'],
                        classification=label))
    return sorted(out,key=lambda x:x['identity_impact'],reverse=True)

def perturb(p,top_n=15):
    a=arrays(p); base=deterministic(p,a); out=[]
    for i in np.argsort(a['parts'])[::-1][:top_n]:
        ds={}; ma=0; fail=False
        for pct in (-.3,-.2,-.1,.1,.2,.3):
            x=a['parts'].copy(); x[i]*=1+pct; m=deterministic(p,a,x); d=m['identity_score']-base['identity_score']
            ds[f'{pct:+.0%}']=float(d); ma=max(ma,abs(d)); fail|=not m['hard_pass']
        label='FRAGILE / PRECISION CRITICAL' if fail or ma>=.06 else 'CONTROLLED TUNING LEVER' if ma>=.03 else 'ROBUST TUNING LEVER'
        out.append(dict(material=a['names'][i],parts_per_1000=float(a['parts'][i]),
                        max_abs_identity_change=float(ma),any_hard_gate_failure=bool(fail),
                        classification=label,deltas=ds))
    return sorted(out,key=lambda x:x['max_abs_identity_change'],reverse=True)

def feature(p):
    fam=sorted(PHASE_COEFF); fi={f:i for i,f in enumerate(fam)}; ft=np.zeros((4,len(fam))); mp={}
    for r in p['rows']:
        mp[r['name']]=float(r['parts']); k=fi[r['family']]
        for t in range(4): ft[t,k]+=float(r['coav_center'][t])
    v=ft.flatten(); v/=np.linalg.norm(v) or 1
    return v,mp

def matcos(a,b):
    names=sorted(set(a)|set(b)); return cosine([a.get(n,0) for n in names],[b.get(n,0) for n in names])

def collision_analysis(profiles):
    feats={p['target']['code']:feature(p) for p in profiles}; out=[]
    for pa,pb in itertools.combinations(profiles,2):
        ca=pa['target']['code']; cb=pb['target']['code']; va,ma=feats[ca]; vb,mb=feats[cb]
        fs=cosine(va,vb); ms=matcos(ma,mb); same=pa['target']['family']==pb['target']['family']; sim=.65*fs+.35*ms
        if sim>=.82 or (same and sim>=.76):
            label='CRITICAL COLLISION' if sim>=.90 else 'HIGH COLLISION' if sim>=.84 else 'WATCH'
            out.append(dict(code_a=ca,target_a=pa['target']['target'],code_b=cb,target_b=pb['target']['target'],
                            same_family=same,family_time_similarity=fs,material_similarity=ms,
                            combined_similarity=sim,classification=label))
    return sorted(out,key=lambda x:x['combined_similarity'],reverse=True)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('input_json',type=Path); ap.add_argument('--out-dir',type=Path,required=True)
    ap.add_argument('--simulations',type=int,default=2000); ap.add_argument('--seed',type=int,default=5602); args=ap.parse_args()
    args.out_dir.mkdir(parents=True,exist_ok=True)
    data=json.loads(args.input_json.read_text(encoding='utf-8')); profiles=data['profiles']; summary=[]; detail={}
    for i,p in enumerate(profiles):
        code=p['target']['code']; mc=monte_carlo(p,args.simulations,args.seed+i*7919); ab=ablation(p); pe=perturb(p)
        state='RC1 ROBUST' if mc['pass_probability']>=.90 else 'RC1 CONDITIONAL' if mc['pass_probability']>=.70 else 'REBUILD / HOLD'
        summary.append(dict(code=code,family=p['target']['family'],target=p['target']['target'],formula_hash=p.get('hash',''),
                            rows=len(p['rows']),desk_score=p.get('final_score',0),
                            monte_carlo_pass_probability=mc['pass_probability'],
                            marker_coverage_probability=mc['marker_coverage_probability'],
                            phase_pass_probability=mc['phase_pass_probability'],
                            temporal_pass_probability=mc['temporal_pass_probability'],
                            dominance_pass_probability=mc['dominance_pass_probability'],
                            critical_materials=sum(x['classification']=='IDENTITY CRITICAL' for x in ab),
                            fragile_materials=sum(x['classification']=='FRAGILE / PRECISION CRITICAL' for x in pe),
                            rc1_state=state))
        detail[code]=dict(target=p['target'],monte_carlo=mc,ablation=ab,perturbation=pe,rc1_state=state)
    collisions=collision_analysis(profiles)
    result=dict(input=str(args.input_json),simulations=args.simulations,seed=args.seed,summary=summary,profiles=detail,collisions=collisions)
    (args.out_dir/'engine_v2_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    with (args.out_dir/'engine_v2_summary.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(summary[0])); w.writeheader(); w.writerows(summary)
    fields=list(collisions[0]) if collisions else ['code_a','target_a','code_b','target_b','same_family','family_time_similarity','material_similarity','combined_similarity','classification']
    with (args.out_dir/'engine_v2_collisions.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(collisions)
    with (args.out_dir/'engine_v2_ablation.csv').open('w',newline='',encoding='utf-8-sig') as f:
        fields=['code','target','material','parts_per_1000','identity_impact','ablated_identity_score','ablated_hard_pass','classification']
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        for code,d in detail.items():
            for r in d['ablation']: w.writerow(dict(code=code,target=d['target']['target'],**r))
    with (args.out_dir/'engine_v2_perturbation.csv').open('w',newline='',encoding='utf-8-sig') as f:
        fields=['code','target','material','parts_per_1000','max_abs_identity_change','any_hard_gate_failure','classification','deltas_json']
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        for code,d in detail.items():
            for r in d['perturbation']:
                w.writerow(dict(code=code,target=d['target']['target'],material=r['material'],parts_per_1000=r['parts_per_1000'],
                                max_abs_identity_change=r['max_abs_identity_change'],
                                any_hard_gate_failure=r['any_hard_gate_failure'],classification=r['classification'],
                                deltas_json=json.dumps(r['deltas'],separators=(',',':'))))
    sha=hashlib.sha256(args.input_json.read_bytes()).hexdigest()
    (args.out_dir/'ENGINE_V2_README.md').write_text(
        f"# Verification Engine V2 Results\n\nInput: `{args.input_json.name}`\nSHA-256: `{sha}`\n"
        f"Simulations/profile: {args.simulations}\nSeed: {args.seed}\n\n"
        "RC1 ROBUST >=90%; CONDITIONAL 70-89.99%; HOLD below 70%.\n\n"
        "Computational robustness only; not measured headspace or physical equivalence.\n",
        encoding='utf-8')
if __name__=='__main__': main()
