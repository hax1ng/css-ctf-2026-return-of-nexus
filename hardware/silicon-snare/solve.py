# Z3 model of the traced gate netlist. Solve for the 32-bit input (I00..I31) that
# drives OVERRIDE high, then re-check UNSAT to prove the solution is unique.
from z3 import *
from parse_svg import paths
# Circuit path endpoints traced from the supplied SVG; see analysis.md.
end={
65:'s00',66:'s00',67:'f00',68:'f00',69:'f01',70:'f01',71:'s01',72:'s01',73:'f02',74:'f02',75:'s02',76:'s02',77:'m20',78:'m20',79:'f03',80:'f03',81:'f04',82:'f04',83:'f05',84:'f05',85:'s03',86:'s03',87:'m21',88:'m21',89:'s04',90:'s04',91:'s05',92:'s05',93:'f06',94:'f06',95:'f07',96:'f07',97:'f08',98:'f08',99:'f09',100:'f09',101:'n00',102:'f0a',103:'f0a',104:'n01',105:'s06',106:'s06',107:'n02',108:'s07',109:'s07',110:'n03',111:'s08',112:'s08',113:'n04',114:'f0b',115:'f0b',116:'f0c',117:'f0c',118:'f0d',119:'f0d',120:'s09',121:'s09',122:'f0e',123:'f0e',124:'s0a',125:'s0a',126:'n05',127:'s0b',128:'s0b',129:'s0c',130:'s0c',131:'m22',132:'m22',133:'f0f',134:'f0f',135:'f10',136:'f10',137:'f11',138:'f11',139:'f12',140:'f12',141:'f13',142:'f13',143:'OVERRIDE'}
start={
65:'m10',66:'m00',67:'m18',68:'m08',69:'s00',70:'f00',71:'m14',72:'m04',73:'m1c',74:'m0c',75:'s01',76:'f02',77:'s02',78:'s01',79:'f01',80:'m20',81:'m12',82:'m02',83:'m1a',84:'m0a',85:'f04',86:'f05',87:'s03',88:'f04',89:'m16',90:'m06',91:'m1e',92:'m0e',93:'s05',94:'s04',95:'f06',96:'m21',97:'f03',98:'f07',99:'m11',100:'m01',101:'f09',102:'m19',103:'m09',104:'f0a',105:'n00',106:'n01',107:'s06',108:'m05',109:'m15',110:'s07',111:'m0d',112:'m1d',113:'s08',114:'n04',115:'n03',116:'f0b',117:'n02',118:'m13',119:'m03',120:'m1b',121:'m0b',122:'s09',123:'f0d',124:'m07',125:'m17',126:'s0a',127:'m1f',128:'m0f',129:'n05',130:'s0b',131:'s0c',132:'n05',133:'m22',134:'f0e',135:'f0f',136:'f0c',137:'f08',138:'f10',139:'I03',140:'I01',141:'f12',142:'f11',143:'f13'}
# Shift gate A=pointed input, B=flat input. Output is Y0=A OR B or Y1=A AND NOT B.
shift={
's00':(65,66,1),'s01':(71,72,1),'s02':(75,76,1),'s03':(85,86,1),
's04':(89,90,1),'s05':(91,92,1),'s06':(105,106,0),'s07':(108,109,0),
's08':(111,112,0),'s09':(120,121,1),'s0a':(124,125,0),
's0b':(127,128,1),'s0c':(129,130,1)}

def model(extra=[]):
 s=Solver(); xs=[Bool(f'I{i:02}') for i in range(32)]; ws={i:Bool(f'W{i:03}') for i in range(1,144)}
 for i in range(32):
  s.add(ws[2*i+1]==xs[(i+7)%32]);s.add(ws[2*i+2]==xs[i])
 s.add(ws[139]==xs[3],ws[140]==xs[1])
 inbound={}
 for i in range(32):inbound[f'm{i:02x}']=[2*i+1,2*i+2]
 for i,g in end.items():inbound.setdefault(g,[]).append(i)
 out={}
 for i,g in start.items():out.setdefault(g,[]).append(i)
 for g,ids in inbound.items():
  if g.startswith('m'):
   assert len(ids)==2,(g,ids)
   val=Xor(ws[ids[0]],ws[ids[1]])
  elif g.startswith('f'):
   assert len(ids)==2,(g,ids)
   val=And(ws[ids[0]],ws[ids[1]])
  elif g.startswith('n'):
   assert len(ids)==1,(g,ids)
   val=Not(ws[ids[0]])
  elif g.startswith('s'):
   A,B,y=shift[g]; assert set(ids)=={A,B},(g,ids,A,B)
   val=Or(ws[A],ws[B]) if y==0 else And(ws[A],Not(ws[B]))
  elif g=='OVERRIDE':
   assert ids==[143]
   continue
  else: raise ValueError(g)
  if g in out:
   for i in out[g]:s.add(ws[i]==val)
  else: print('unused',g)
 for c in extra:s.add(c)
 s.add(ws[143])
 return s,xs,ws

if __name__=='__main__':
 s,xs,ws=model(); print('SAT:',s.check())
 if s.check()==sat:
  m=s.model(); bits=''.join('1' if is_true(m.eval(x)) else '0' for x in xs);print(bits)
  print('ones', [i for i,b in enumerate(bits) if b=='1'])
  s.add(Or(*[x!=m.eval(x) for x in xs]));print('second?',s.check())
