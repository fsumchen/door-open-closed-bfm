#!/usr/bin/env python3
"""Exploratory session-held-out nearest-centroid baseline (Python standard library)."""
import argparse,csv,json,math,statistics
from collections import Counter
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('windows',type=Path); p.add_argument('--output',type=Path,required=True); a=p.parse_args()
    with a.windows.open(newline='',encoding='utf-8') as f: rows=list(csv.DictReader(f))
    if not rows: raise SystemExit('No windows to evaluate')
    feature_cols=[k for k in rows[0] if k.endswith('_mean') or k.endswith('_sd')]
    sessions=sorted({r['session_id'] for r in rows}); result={'status':'exploratory_only','method':'standardized nearest centroid','split':'leave one session out','feature_columns':feature_cols,'folds':[]}
    for test_session in sessions:
        train=[r for r in rows if r['session_id']!=test_session]; test=[r for r in rows if r['session_id']==test_session]
        train_labels=sorted({r['door_state'] for r in train}); test_labels=sorted({r['door_state'] for r in test})
        fold={'test_session':test_session,'train_windows':len(train),'test_windows':len(test),'train_classes':Counter(r['door_state'] for r in train),'test_classes':Counter(r['door_state'] for r in test)}
        fold['train_classes']=dict(fold['train_classes']); fold['test_classes']=dict(fold['test_classes'])
        if len(train_labels)<2:
            fold['status']='skipped: training fold lacks both classes'; result['folds'].append(fold); continue
        mu=[]; sd=[]
        for col in feature_cols:
            vals=[float(r[col]) for r in train]; mu.append(statistics.mean(vals)); sd.append(statistics.pstdev(vals) or 1.0)
        centroids={lab:[statistics.mean((float(r[c])-m)/s for r in train if r['door_state']==lab) for c,m,s in zip(feature_cols,mu,sd)] for lab in train_labels}
        cm={lab:{p:0 for p in train_labels} for lab in train_labels}
        for r in test:
            x=[(float(r[c])-m)/s for c,m,s in zip(feature_cols,mu,sd)]
            pred=min(train_labels,key=lambda lab:sum((u-v)**2 for u,v in zip(x,centroids[lab])))
            cm[r['door_state']][pred]=cm.get(r['door_state'],{}).get(pred,0)+1
        correct=sum(cm.get(l,{}).get(l,0) for l in train_labels); n=len(test)
        fold.update({'status':'scored; interpret cautiously','accuracy':correct/n if n else None,'confusion_matrix':cm,'test_class_coverage':len(test_labels)})
        result['folds'].append(fold)
    scored=[f for f in result['folds'] if f['status'].startswith('scored')]
    result['conclusion']='Do not report as final performance: same-day sessions, severe class/session imbalance, and interval labels partly assumed.'
    if scored: result['mean_fold_accuracy']=sum(f['accuracy'] for f in scored)/len(scored)
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(a.output.read_text())
if __name__=='__main__': main()
