#!/usr/bin/env python3
"""Create an exploratory SCIDX-by-time heatmap from extracted phone BFM reports."""
import argparse,csv,json,math
from collections import defaultdict,Counter
from pathlib import Path

def hue(deg): return f'hsl({deg:.1f},68%,47%)'

def main():
 p=argparse.ArgumentParser(description=__doc__); p.add_argument('input',type=Path); p.add_argument('--output',type=Path,required=True); p.add_argument('--bin-seconds',type=int,default=5); a=p.parse_args()
 bins=defaultdict(lambda:defaultdict(list)); labels=defaultdict(Counter); max_t=0; tones=None
 with a.input.open(newline='',encoding='utf-8') as f:
  for r in csv.DictReader(f):
   t=float(r['time_s']); b=int(t//a.bin_seconds); max_t=max(max_t,t); labels[b][r['door_state']]+=1
   sc=json.loads(r['scidx']); ph=json.loads(r['phi_code']); tones=sc
   for idx,code in zip(sc,ph):
    rad=2*math.pi*(code+.5)/64; bins[b][idx].append((math.sin(rad),math.cos(rad)))
 if not tones: raise SystemExit('No decoded tones')
 ncols=int(max_t//a.bin_seconds)+1; ordered=sorted(tones); cellw=6; cellh=4; left=85; top=45; plotw=ncols*cellw; ploth=len(ordered)*cellh; width=left+plotw+30; height=top+ploth+115
 out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">','<rect width="100%" height="100%" fill="white"/>',f'<text x="{left+plotw/2}" y="24" text-anchor="middle" font-family="sans-serif" font-size="16">{a.input.stem}: phone BFM φ angle by tone and time</text>']
 for b in range(ncols):
  for row,sc in enumerate(ordered):
   vals=bins[b].get(sc,[])
   if not vals: continue
   si=sum(x for x,y in vals)/len(vals); co=sum(y for x,y in vals)/len(vals); deg=(math.degrees(math.atan2(si,co))%360)
   out.append(f'<rect x="{left+b*cellw}" y="{top+row*cellh}" width="{cellw+0.2}" height="{cellh+0.2}" fill="{hue(deg)}"/>')
 # state strip from report labels, directly below heatmap
 sy=top+ploth+12
 for b in range(ncols):
  if labels[b]:
   state=labels[b].most_common(1)[0][0]; color={'open':'#3667a8','closed':'#d27b29'}.get(state,'#999999')
   out.append(f'<rect x="{left+b*cellw}" y="{sy}" width="{cellw+0.2}" height="12" fill="{color}"/>')
 for sec in range(0,721,120):
  x=left+int(sec/a.bin_seconds)*cellw
  out.append(f'<line x1="{x}" y1="{top}" x2="{x}" y2="{sy+18}" stroke="#999" stroke-width="0.5"/>')
  out.append(f'<text x="{x}" y="{sy+38}" text-anchor="middle" font-family="sans-serif" font-size="11">{sec}</text>')
 out += [f'<text x="{left+plotw/2}" y="{height-14}" text-anchor="middle" font-family="sans-serif" font-size="12">Elapsed capture time (s); color is circular mean φ code, hue 0–360°</text>',f'<text x="18" y="{top+ploth/2}" transform="rotate(-90 18 {top+ploth/2})" text-anchor="middle" font-family="sans-serif" font-size="12">VHT SCIDX tone ({ordered[0]} to {ordered[-1]})</text>',f'<text x="{left}" y="{sy+10}" font-family="sans-serif" font-size="10">Closed</text>',f'<text x="{left+65}" y="{sy+10}" font-family="sans-serif" font-size="10">Open</text>',f'<rect x="{left+39}" y="{sy}" width="10" height="12" fill="#d27b29"/>',f'<rect x="{left+100}" y="{sy}" width="10" height="12" fill="#3667a8"/>','</svg>']
 a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text('\n'.join(out),encoding='utf-8'); print(f'Wrote {a.output}')
if __name__=='__main__': main()
