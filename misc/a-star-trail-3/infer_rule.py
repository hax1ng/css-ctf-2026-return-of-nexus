#!/usr/bin/env python3
"""Infer A Star Trail 3's missing edge-generation rule from the related Star Trail 2 map."""
import zipfile,re,collections,math
import numpy as np
from scipy.spatial import Delaunay,cKDTree
z=zipfile.ZipFile('map.zip')
ids=[];xy=[]; links={}
for n in z.namelist():
 if not n.endswith('.md'):continue
 s=z.read(n).decode();m=re.search(r'^# (\w+)\n\nCoords: ([\d.]+), ([\d.]+)$',s,re.M)
 assert m
 id,x,y=m.groups();ids.append(id);xy.append((float(x),float(y)));links[id]=set(re.findall(r'\[\[(\w+)\]\]',s))
xy=np.array(xy); idx={s:i for i,s in enumerate(ids)}
actual={tuple(sorted((idx[u],idx[v]))) for u,ns in links.items() for v in ns}
assert sum(map(len,links.values()))==2*len(actual)
print('N',len(ids),'edges',len(actual),'degree distribution',collections.Counter(map(len,links.values())).most_common(15),flush=True)
lengths=np.array([np.linalg.norm(xy[a]-xy[b]) for a,b in actual])
print('edge length min median max',lengths.min(),np.median(lengths),lengths.max(),flush=True)

def report(name,edges):
 missing=actual-edges; extra=edges-actual
 print(name,'candidate',len(edges),'common',len(actual&edges),'missing',len(missing),'extra',len(extra),flush=True)
 if len(missing)<20:print('missing list',[(ids[a],ids[b]) for a,b in missing],flush=True)
 if len(extra)<20:print('extra list',[(ids[a],ids[b]) for a,b in extra],flush=True)

tri=Delaunay(xy)
edges={tuple(sorted((int(a),int(b)))) for simplex in tri.simplices for a,b in ((simplex[0],simplex[1]),(simplex[1],simplex[2]),(simplex[0],simplex[2]))}
report('Delaunay',edges)
tree=cKDTree(xy)
for k in (3,4,5,6,8,10,12):
 d,ne=tree.query(xy,k=k+1)
 directed={(i,int(j)) for i,row in enumerate(ne) for j in row[1:]}
 union={tuple(sorted((i,j))) for i,j in directed}
 mutual={tuple(sorted((i,j))) for i,j in directed if (j,i) in directed}
 report('knn union '+str(k),union);report('knn mutual '+str(k),mutual)
for r in (2,3,4,5,6):report('radius '+str(r),tree.query_pairs(r))
