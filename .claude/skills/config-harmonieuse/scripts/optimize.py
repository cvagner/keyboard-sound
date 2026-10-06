"""Affectation touche -> note par recuit simulé.

Usage : python3 optimize.py [NB_RELANCES] (défaut 6)
Variables : W="rough,leap,stab,end,spread,reg" (poids), REPEAT (coût d'une note répétée),
OUT (fichier de configuration produit, défaut piano-harmonie-opt.json)."""
import collections
import glob
import json
import math
import os
import random
import sys

import numpy as np

from corpus import load_corpus, to_keys
from evaluate import REPO
from model import INSTAB, LAG_W, MAX_LAG, leap_cost, roughness

# Touches à note imposée (rôle sémantique)
FIXED = {
    'space': 48,          # C3 : basse de tonique à chaque mot
    'return': 36,         # C2 : fin de paragraphe
    'comma': 60,          # . et ; -> C4 : cadence parfaite (puis espace = C3)
    'm': 67,              # , et ? -> G4 : dominante, suspension / question
    'dot': 74,            # : -> D5 : degré instable, annonce
    'forward slash': 72,  # ! -> C5 : tonique éclatante
}
# Notes candidates pour les autres touches : pentatonique de do, G3..C6
CANDIDATES = [55, 57, 60, 62, 64, 67, 69, 72, 74, 76, 79, 81, 84]
ALL_KEYS = (list('qwertyuiopasdfghjklzxcvbn') + ['semicolon', 'quote', 'backtick', 'minus', 'equals',
            'square bracket open', 'square bracket close', 'backslash'] + list('1234567890')
            + list(FIXED))
# Poids par défaut : ceux de config/piano-harmonie3.json
W_ROUGH, W_LEAP, W_STAB, W_END, W_SPREAD, W_REG = (float(x) for x in os.environ.get('W', '1.0,1.0,0.4,0.6,4.0,0.1').split(','))


def stats(keys):
    idx = {k: i for i, k in enumerate(ALL_KEYS)}
    seq = np.array([idx[k] for k in keys if k in idx])
    n = len(ALL_KEYS)
    uni = np.bincount(seq, minlength=n) / len(seq)
    # co-présence (notes qui sonnent ensemble), pondérée par la décroissance
    co = np.zeros((n, n))
    for lag in range(1, MAX_LAG + 1):
        np.add.at(co, (seq[:-lag], seq[lag:]), LAG_W[lag - 1])
    co /= len(seq)
    # enchaînement mélodique : touche suivante, l'espace étant transparente (poids 0.5)
    sp = idx['space']
    big = np.zeros((n, n))
    np.add.at(big, (seq[:-1], seq[1:]), 1.0)
    across = (seq[1:-1] == sp)
    np.add.at(big, (seq[:-2][across], seq[2:][across]), 0.5)
    big[sp, :] = 0
    big[:, sp] = 0
    np.fill_diagonal(big, 0)  # une lettre doublée reste la même note : pas de coût
    big /= len(seq)
    # fin de mot : touche suivie d'un espace ou d'une ponctuation
    ends = np.zeros(n)
    stops = {idx[k] for k in ('space', 'return', 'comma', 'm', 'dot', 'forward slash')}
    is_stop = np.isin(seq[1:], list(stops)) & ~np.isin(seq[:-1], list(stops))
    np.add.at(ends, seq[:-1][is_stop], 1.0)
    ends /= len(seq)
    return uni, co, big, ends


class Problem:
    def __init__(self, keys):
        self.uni, self.co, self.big, self.ends = stats(keys)
        self.notes = np.arange(24, 100)
        lo, hi = self.notes[0], self.notes[-1]
        self.R = np.array([[roughness(a, b) for b in self.notes] for a in self.notes])
        self.L = np.array([[leap_cost(a - b) for b in self.notes] for a in self.notes])
        self.off = lo
        self.instab = np.array([INSTAB.get(m % 12, 1.0) for m in self.notes])
        self.free = [i for i, k in enumerate(ALL_KEYS) if k not in FIXED]
        self.melodic = np.array([k not in ('space', 'return') for k in ALL_KEYS])

    def cost(self, p, detail=False):
        i = p - self.off
        rough = (self.co * self.R[np.ix_(i, i)]).sum()
        leap = (self.big * self.L[np.ix_(i, i)]).sum()
        stab = (self.uni * self.instab[i]).sum()
        end = (self.ends * self.instab[i]).sum() / max(self.ends.sum(), 1e-9)
        use = collections.defaultdict(float)
        for k in np.flatnonzero(self.melodic):
            use[p[k]] += self.uni[k]
        tot = sum(use.values())
        spread = sum((u / tot) ** 2 for u in use.values())  # Herfindahl : 1/nb notes effectives
        reg = (self.uni * self.melodic * np.maximum(0, np.abs(p - 69) - 7) ** 2).sum() / 9
        parts = dict(rough=W_ROUGH * rough, leap=W_LEAP * leap, stab=W_STAB * stab,
                     end=W_END * end, spread=W_SPREAD * spread, reg=W_REG * reg)
        return parts if detail else sum(parts.values())


def anneal(pb, seed, iters=60000):
    rng = random.Random(seed)
    p = np.array([FIXED.get(k, rng.choice(CANDIDATES)) for k in ALL_KEYS])
    c = pb.cost(p)
    best, best_c = p.copy(), c
    t0, t1 = 0.02, 0.00005
    for it in range(iters):
        t = t0 * (t1 / t0) ** (it / iters)
        q = p.copy()
        if rng.random() < 0.5:
            q[rng.choice(pb.free)] = rng.choice(CANDIDATES)
        else:
            a, b = rng.sample(pb.free, 2)
            q[a], q[b] = q[b], q[a]
        cq = pb.cost(q)
        if cq < c or rng.random() < math.exp((c - cq) / t):
            p, c = q, cq
            if c < best_c:
                best, best_c = p.copy(), c
    return best, best_c


def write_config(assign, uni, path):
    """Écrit la configuration au format du dépôt : touches groupées par note, de la plus grave à la plus aiguë."""
    files = {int(os.path.basename(f)[:2]) + 20: 'piano/' + os.path.basename(f)
             for f in glob.glob(os.path.join(REPO, 'sounds', 'piano', '*.wav'))}
    groups = collections.defaultdict(list)
    for k, m in assign.items():
        groups[m].append(k)
    blocks = []
    for m in sorted(groups):
        ks = sorted(groups[m], key=lambda k: (-uni[ALL_KEYS.index(k)], k))
        blocks.append([f'    {json.dumps(k)}: {json.dumps(files[m], ensure_ascii=False)}' for k in ks])
    with open(path, 'w', encoding='utf-8') as f:
        f.write('{\n' + ',\n\n'.join(',\n'.join(b) for b in blocks) + '\n}\n')


if __name__ == '__main__':
    pb = Problem(to_keys('\n'.join(load_corpus())))
    runs = sorted((anneal(pb, s) for s in range(int(sys.argv[1]) if len(sys.argv) > 1 else 6)),
                  key=lambda r: r[1])
    for p, c in runs:
        print(f'{c:.5f}', ' '.join(f'{k}={m}' for k, m in zip(ALL_KEYS, p) if k not in FIXED))
    best = runs[0][0]
    print({k: round(float(v), 5) for k, v in pb.cost(best, detail=True).items()})
    out = os.environ.get('OUT', 'piano-harmonie-opt.json')
    write_config({k: int(m) for k, m in zip(ALL_KEYS, best)}, pb.uni, out)
    print('->', out)
