#!/usr/bin/env python3
"""Explore graph ambiguity in the supplied 25k-coordinate map; no inferred edges are claimed official."""
import zipfile,re,sys,collections,heapq,math
import numpy as np
from scipy.spatial import cKDTree,Delaunay
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components,dijkstra
zip_path=sys.argv[1] if len(sys.argv)>1 else 'map2.zip'
ids=[]; xy=[]
with zipfile.ZipFile(zip_path) as z:
 for n in z.namelist():
  if not n.endswith('.md'): continue
  s=z.read(n).decode()
  m=re.fullmatch(r'# ([A-Za-z0-9]{6})\n\nCoords: ([0-9.]+), ([0-9.]+)\n\n\n\[CORRUPTED\]\n',s)
  assert m and m.group(1)==n.rsplit('/',1)[-1][:-3]
  ids.append(m.group(1)); xy.append(tuple(map(float,m.groups()[1:])))
xy=np.array(xy); ids=np.array(ids); index={s:i for i,s in enumerate(ids)}
s=index['iJ2ZcO'];t=index['pJk9vy']; tree=cKDTree(xy)
print('nodes',len(ids),'source',xy[s],'target',xy[t], 'direct_distance',np.linalg.norm(xy[s]-xy[t]),flush=True)

def report(name,edges):
  e=np.array(list(edges),dtype=int)
  r,c=e[:,0],e[:,1]; dist=np.linalg.norm(xy[r]-xy[c],axis=1)
  a=csr_matrix((dist,(r,c)),shape=(len(ids),len(ids))); a=a.maximum(a.T)
  ncomp,lab=connected_components(a,directed=False)
  lengths=np.bincount(lab)
  ds,pred=dijkstra(a,indices=s,return_predecessors=True)
  if not np.isfinite(ds[t]): print(name,'edges',len(e),'components',ncomp,'largest',max(lengths),'NO ROUTE',flush=True);return
  path=[]; cur=t
  while cur!=-9999:
    path.append(cur)
    if cur==s:break
    cur=pred[cur]
  path=path[::-1]; flag=''.join(ids[v][i%6] for i,v in enumerate(path))
  print(name,'edges',len(e),'components',ncomp,'largest',max(lengths),'steps',len(path),'length',round(ds[t],6),'flag_prefix',flag[:24],'flag_suffix',flag[-12:],flush=True)
  return flag

# Fixed radius models.
for radius in (0.8,1.0,1.2,1.5,2.0):
 pairs=tree.query_pairs(radius)
 report(f'radius={radius}',pairs)
# Mutual and union k-NN models.
for k in (4,6,8,10):
 d,near=tree.query(xy,k=k+1)
 directed={(i,int(j)) for i,row in enumerate(near) for j in row[1:]}
 pairs={tuple(sorted((i,j))) for i,j in directed}
 report(f'knn-union={k}',pairs)
 mutual={tuple(sorted((i,j))) for i,j in directed if (j,i) in directed}
 report(f'knn-mutual={k}',mutual)
# Delaunay model.
tri=Delaunay(xy)
edges=set()
for a,b,c in tri.simplices:
 edges.update((tuple(sorted(p)) for p in ((a,b),(b,c),(a,c))))
report('delaunay',edges)
