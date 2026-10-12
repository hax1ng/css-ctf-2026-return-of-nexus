# Parse schematic.svg: extract the 143 coloured wire paths + gate-label positions,
# and report each wire's endpoints with the nearest gate labels (for manual tracing).
from lxml import etree
import re, math
r=etree.parse('schematic.svg')
groups={g.get('id'):g for g in r.xpath('//*[local-name()="g"][@id]')}
labels={}
for g in groups.values():
 if g.get('id','').startswith('text_'):
  txt=''.join(x.text or '' for x in g if isinstance(x,etree._Comment)).strip()
  if re.fullmatch(r'[msfn][0-9a-f]{2}',txt):
   t=g.xpath('.//*[@transform]')[0].get('transform'); x,y=map(float,re.search(r'translate\(([^ ]+) ([^\)]+)\)',t).groups()); labels[txt]=(x,y)
paths={}
for i in range(1,144):
 p=groups[f'line2d_{i}'][0]; d=p.get('d'); nums=list(map(float,re.findall(r'-?\d+(?:\.\d+)?',d))); color=re.search(r'stroke: (#[0-9a-f]+)',p.get('style')).group(1)
 paths[i]={'start':tuple(nums[:2]),'end':tuple(nums[-2:]),'color':color,'all':list(zip(nums[::2],nums[1::2]))}
def near(pt):
 a=sorted(((math.dist(pt,xy),name) for name,xy in labels.items()))[:3]
 return ','.join(f'{name}:{dist:.1f}' for dist,name in a)
if __name__=='__main__':
 for i,p in paths.items(): print(f'{i:03} {p["color"]} {p["start"]} {near(p["start"]):25} -> {p["end"]} {near(p["end"])}')
