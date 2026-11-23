#!/usr/bin/env python3
"""Make fixed-duration BFM windows with compact angle-summary features (stdlib only)."""
import argparse, csv, json, math, statistics
from collections import defaultdict, Counter
from pathlib import Path

def parse_array(s):
    return json.loads(s)

def report_features(row):
    phi = parse_array(row['phi_code'])
    psi = parse_array(row['psi_code'])
    if not phi or len(phi) != len(psi):
        raise ValueError(f"Bad angle arrays in {row['session_id']} at {row['time_s']}")
    n=len(phi); mid=n//2
    def block(a,b):
        ps=[2*math.pi*(v+0.5)/64 for v in phi[a:b]]
        qs=[math.pi/2*(v+0.5)/16 for v in psi[a:b]]
        return {
            'phi_sin':sum(math.sin(v) for v in ps)/len(ps),
            'phi_cos':sum(math.cos(v) for v in ps)/len(ps),
            'psi_mean':sum(qs)/len(qs),
            'psi_sd':statistics.pstdev(qs) if len(qs)>1 else 0.0,
        }
    lo,hi=block(0,mid),block(mid,n)
    return {f'{k}_{side}':v for side,d in [('low',lo),('high',hi)] for k,v in d.items()}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('inputs', nargs='+', type=Path)
    ap.add_argument('--window-seconds',type=float,default=30)
    ap.add_argument('--min-reports',type=int,default=5)
    ap.add_argument('--min-purity',type=float,default=.8)
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args(); groups=defaultdict(list); keys=None
    for path in a.inputs:
        with path.open(newline='',encoding='utf-8') as f:
            for row in csv.DictReader(f):
                t=float(row['time_s']); key=(row['session_id'],int(t//a.window_seconds))
                feats=report_features(row); keys=list(feats)
                groups[key].append((t,row['door_state'],feats))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    kept=0
    with a.output.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=['session_id','window_start_s','window_end_s','door_state','reports','label_purity']+[f'{k}_{stat}' for k in keys for stat in ('mean','sd')])
        writer.writeheader()
        for (session,bucket),rows in sorted(groups.items()):
            labels=Counter(r[1] for r in rows); label,count=labels.most_common(1)[0]; purity=count/len(rows)
            if len(rows)<a.min_reports or purity<a.min_purity: continue
            out={'session_id':session,'window_start_s':round(bucket*a.window_seconds,3),'window_end_s':round((bucket+1)*a.window_seconds,3),'door_state':label,'reports':len(rows),'label_purity':round(purity,4)}
            for k in keys:
                vals=[r[2][k] for r in rows]
                out[f'{k}_mean']=round(statistics.mean(vals),8); out[f'{k}_sd']=round(statistics.pstdev(vals),8)
            writer.writerow(out); kept+=1
    print(f'Wrote {kept} labeled windows to {a.output}')
if __name__=='__main__': main()
