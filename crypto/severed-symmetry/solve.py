#!/usr/bin/env python3
"""Recover the hidden triangular/Oil-and-Vinegar structure (run with sage-run)."""
import json
import random
import time
from collections import defaultdict

import numpy as np
from sage.all import GF, matrix, vector

P = 17
N = 32
M = 34
F = GF(P)

def log(*args):
    print(time.strftime('%H:%M:%S'), *args, flush=True)

data = json.load(open('out.txt'))
polys = data['public_key']['polynomials']
cipher = np.array(data['ciphertext']['blocks'], dtype=np.int64)
log('loaded', [len(a) for a in polys], 'blocks', len(cipher))

monomials = sorted({tuple(mon) for poly in polys for _, mon in poly})
monidx = {mon:i for i, mon in enumerate(monomials)}
degree = np.array([len(mon) for mon in monomials])
coeff = np.zeros((M, len(monomials)), dtype=np.float32)
for i, poly in enumerate(polys):
    for c, mon in poly:
        coeff[i, monidx[tuple(mon)]] = c
log('unique monomials', len(monomials))

random.seed(280028)
quartic = np.where(degree == 4)[0]
sample = random.sample(list(quartic), 300)
Q = matrix(F, M, len(sample), [int(v) for v in coeff[:, sample].ravel()])
Wbasis = Q.left_kernel().basis_matrix()
assert Wbasis.nrows() == 16, Wbasis.nrows()
wb = np.array([[int(v) for v in row] for row in Wbasis], dtype=np.float32)
Wcoeff = np.mod(np.rint(wb @ coeff).astype(np.int64), P)
assert np.all(Wcoeff[:, degree >= 3] == 0), 'quartic cancellation did not imply cubic cancellation'
log('recovered 16 quadratic outer coordinates')

cW = Wcoeff[:, monidx[()]]
LW = np.array([[Wcoeff[i, monidx[(j,)]] for j in range(N)] for i in range(16)], dtype=np.int64)
Hs = np.zeros((16, N, N), dtype=np.int64)
for i in range(16):
    for a in range(N):
        for b in range(a, N):
            v = Wcoeff[i, monidx[(a,b)]]
            Hs[i,a,b] = Hs[i,b,a] = (2*v if a == b else v) % P
stack = matrix(F, 16*N, N, [int(v) for v in Hs.reshape(-1)])
KB = stack.right_kernel().basis_matrix()
assert KB.nrows() == 16, KB.nrows()
B = np.array([[int(v) for v in row] for row in KB], dtype=np.int64).T
D = (LW @ B) % P
Din = np.array([[int(v) for v in row] for row in matrix(F, D.tolist()).inverse()], dtype=np.int64)
assert np.array_equal((D @ Din)%P, np.eye(16, dtype=np.int64))

Ecols = []
current = matrix(F, B.tolist())
for j in range(N):
    candidate = np.zeros(N, dtype=np.int64); candidate[j] = 1
    test = current.augment(matrix(F, N, 1, candidate.tolist()))
    if test.rank() > current.rank():
        Ecols.append(candidate)
        current = test
    if len(Ecols) == 16: break
assert len(Ecols) == 16
E = np.array(Ecols, dtype=np.int64).T
log('common Hessian radical', KB.nrows(), 'complement', len(Ecols))

outidx = []
cur = Wbasis
for j in range(M):
    row = [int(k == j) for k in range(M)]
    test = cur.stack(matrix(F, 1, M, row))
    if test.rank() > cur.rank():
        outidx.append(j)
        cur = test
    if len(outidx) == 18: break
assert len(outidx) == 18
log('independent output coordinates', outidx)

qi = [(i,j,monidx[(i,j)]) for i in range(N) for j in range(i,N)]
def eval_w(X):
    X = np.asarray(X, dtype=np.int64)
    result = (cW + LW @ X) % P
    for a,b,k in qi:
        result = (result + Wcoeff[:,k] * X[a] * X[b]) % P
    return result

def lift(y, target):
    base = (E @ y) % P
    delta = (target - eval_w(base)) % P
    return (base + B @ ((Din @ delta)%P)) % P

target_w = (cipher @ wb.T.astype(np.int64)) % P
for k in range(len(cipher)):
    for _ in range(3):
        y = np.array([random.randrange(P) for _ in range(16)], dtype=np.int64)
        assert np.array_equal(eval_w(lift(y, target_w[k])), target_w[k])
log('all ciphertext fibers lift consistently')

# A float32 dot product is exact here: each sum is at most 58905 * 16 * 16 < 2^24.
mi = np.array([list(mon) + [N]*(4-len(mon)) for mon in monomials], dtype=np.int64)
def eval_public(X):
    X = np.asarray(X, dtype=np.int64)
    extended = np.concatenate([X, np.ones((len(X),1), dtype=np.int64)], axis=1)
    vals = np.ones((len(X), len(monomials)), dtype=np.float32)
    for j in range(4):
        vals *= extended[:, mi[:,j]].astype(np.float32)
    np.mod(vals, P, out=vals)
    raw = vals @ coeff[outidx,:].T
    return np.mod(np.rint(raw).astype(np.int64), P)

y0 = np.zeros(16, dtype=np.int64)
eye = np.eye(16, dtype=np.int64)
points = [y0] + [eye[i] for i in range(16)] + [(2*eye[i])%P for i in range(16)]
pairs = [(i,j) for i in range(16) for j in range(i+1,16)]
points += [(eye[i]+eye[j])%P for i,j in pairs]
blocks_F = []
H = np.zeros((18,16,16), dtype=np.int64)
for k in range(len(cipher)):
    used = points if k == 0 else points[:17]
    X = np.array([lift(y, target_w[k]) for y in used], dtype=np.int64)
    results = eval_public(X)
    f0 = results[0]
    if k == 0:
        f1 = results[1:17]
        f2 = results[17:33]
        diagonal = ((f2 - 2*f1 + f0) * 9) % P
        linear = (f1 - f0 - diagonal) % P
        for i in range(16): H[:,i,i] = (2*diagonal[i]) % P
        for q,(i,j) in enumerate(pairs):
            H[:,i,j] = H[:,j,i] = (results[33+q] - f1[i] - f1[j] + f0) % P
    else:
        diagonal = np.diagonal(H, axis1=1, axis2=2).T * 9 % P
        linear = (results[1:17] - f0 - diagonal) % P
    blocks_F.append(dict(const=f0.tolist(), linear=linear.T.tolist()))
    log('interpolated fiber block',k)

for _ in range(3):
    y = np.array([random.randrange(P) for _ in range(16)],dtype=np.int64)
    x = lift(y, target_w[0])
    real = eval_public(x[None,:])[0]
    pred = (np.array(blocks_F[0]['const']) + np.array(blocks_F[0]['linear']) @ y +
            np.einsum('i,aij,j->a', y, H, y) * 9) % P
    assert np.array_equal(real,pred), (real,pred)
log('verified quadratic restriction at random points')

oilrows=[]
for a in range(18):
    ker = matrix(F, H[a].tolist()).right_kernel().basis_matrix()
    for row in ker:
        test = matrix(F, oilrows+[list(row)])
        if test.rank() > len(oilrows): oilrows.append(list(row))
    if len(oilrows) == 12: break
assert len(oilrows) == 12, len(oilrows)
O = np.array([[int(v) for v in row] for row in oilrows], dtype=np.int64).T
assert all(np.all((O.T @ H[a] @ O)%P == 0) for a in range(18))
log('oil dimension',len(oilrows),'found by Hessian kernels')

Vcols=[]
current=matrix(F,O.tolist())
for j in range(16):
    e = np.zeros(16,dtype=np.int64); e[j]=1
    test=current.augment(matrix(F,16,1,e.tolist()))
    if test.rank()>current.rank():
        current=test; Vcols.append(e)
    if len(Vcols)==4: break
V=np.array(Vcols,dtype=np.int64).T
assert len(Vcols)==4

Hvv = np.array([(V.T @ H[a] @ V)%P for a in range(18)])
Hvo = np.array([(V.T @ H[a] @ O)%P for a in range(18)])
results=[]
for k,block in enumerate(blocks_F):
    linear=np.array(block['linear'],dtype=np.int64)
    results.append(dict(const=block['const'], lv=((linear @ V)%P).tolist(),
                        lo=((linear @ O)%P).tolist(), target=cipher[k,outidx].tolist()))

prepared=dict(p=P,n=N,m=M,Wbasis=[[int(v) for v in row] for row in Wbasis],
              B=B.tolist(),E=E.tolist(),Dinv=Din.tolist(),Wcoeff=Wcoeff[:,degree<=2].tolist(),
              Wmon=[list(monomials[i]) for i in np.where(degree<=2)[0]],
              outidx=outidx,target_w=target_w.tolist(),oil=O.tolist(),vinegar=V.tolist(),
              Hvv=Hvv.tolist(),Hvo=Hvo.tolist(),blocks=results)
with open('prepared.json','w') as fh: json.dump(prepared,fh)
log('wrote prepared.json')
