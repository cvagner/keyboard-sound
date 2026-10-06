"""Évalue des configurations sur un texte : rugosité, dissonances dures,
mélodie, clarté tonale, frappes muettes. Peut aussi rendre une démo WAV.

Usage : python3 evaluate.py config/a.json [config/b.json …]
        python3 evaluate.py --render demo.wav config/a.json
Variable : KPS (frappes par seconde, défaut 6)."""
import glob
import json
import math
import os
import random
import re
import struct
import sys

import numpy as np

from corpus import to_keys
from model import KK_MAJOR, TAU, roughness

KPS = float(os.environ.get('KPS', 6.0))
from wavio import read_wav

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
# a.wav…g.wav : hauteurs mesurées par analyse spectrale (C4…B4 naturels)
SIMPLE = {'c.wav': 60, 'd.wav': 62, 'e.wav': 64, 'f.wav': 65, 'g.wav': 67, 'a.wav': 69, 'b.wav': 71}

TEXT = ("Le matin, la brume glissait lentement sur la rivière. Au loin, une cloche sonnait : "
        "était-ce l'appel du village ou le souvenir d'un rêve ? Personne ne savait vraiment. "
        "Les enfants couraient déjà vers la forêt, où les fougères brillaient encore de rosée. "
        "« Attendez-moi ! » criait la plus petite, en riant. Plus tard, assis près du feu, "
        "chacun raconterait l'été, les orages et les fêtes, comme on ouvre une boîte précieuse.\n"
        "Il faut parfois peu de chose pour qu'une journée ordinaire devienne inoubliable : une "
        "lumière douce, une voix familière, quelques mots écrits à la hâte sur un carnet. "
        "Qui n'a jamais gardé, au fond d'un tiroir, une lettre qu'il ne relira plus ?")


def sound_to_midi(s):
    m = re.match(r'piano/(\d+)-', s)
    return int(m.group(1)) + 20 if m else SIMPLE[s]


def load_config(path):
    return {k: sound_to_midi(v) for k, v in json.load(open(path, encoding='utf-8')).items()}


def timeline(keys, seed=0):
    rng = random.Random(seed)
    t, out = 0.0, []
    for k in keys:
        out.append((t, k))
        gap = 1 / KPS * rng.lognormvariate(0, 0.25)
        if k in ('space', 'comma', 'm'):
            gap *= 1.3  # micro-pause entre les mots
        t += gap
    return out


_R = {}


def R(a, b):
    if (a, b) not in _R:
        _R[(a, b)] = roughness(a, b)
    return _R[(a, b)]


def evaluate(cfg, text=TEXT):
    keys = to_keys(text)
    tl = timeline(keys)
    sounding = []  # (t0, midi)
    rough, hard, pairs_w, muted = [], 0.0, 0.0, 0
    mel, prev = [], None
    pc_w = np.zeros(12)
    for t, k in tl:
        if k not in cfg:
            muted += 1
            continue
        m = cfg[k]
        sounding = [(t0, mm) for t0, mm in sounding if t - t0 < 1.6]
        amps = [(math.exp(-(t - t0) / TAU), mm) for t0, mm in sounding]
        r = sum(a * R(m, mm) for a, mm in amps)
        for i in range(len(amps)):
            for j in range(i + 1, len(amps)):
                r += min(amps[i][0], amps[j][0]) * R(amps[i][1], amps[j][1])
        rough.append(r)
        for a, mm in amps:
            if mm != m:
                pairs_w += a
                if abs(m - mm) % 12 in (1, 6, 11):
                    hard += a
        sounding.append((t, m))
        pc_w[m % 12] += TAU
        if k not in ('space', 'return'):
            if prev is not None:
                mel.append(abs(m - prev))
            prev = m
    # clarté tonale : meilleure corrélation avec les 24 profils de Krumhansl-Kessler
    kk_min = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
    best = max((np.corrcoef(pc_w, np.roll(prof, tonic))[0, 1], tonic, mode)
               for tonic in range(12) for prof, mode in ((KK_MAJOR, 'maj'), (kk_min, 'min')))
    names = ['do', 'do#', 'ré', 'mi♭', 'mi', 'fa', 'fa#', 'sol', 'la♭', 'la', 'si♭', 'si']
    mel = np.array(mel)
    return {
        'rugosité moy.': round(float(np.mean(rough)), 3),
        'rugosité p95': round(float(np.percentile(rough, 95)), 3),
        'dissonances dures %': round(100 * hard / max(pairs_w, 1e-9), 1),
        'saut moyen (½t)': round(float(mel.mean()), 1),
        'sauts > octave %': round(100 * float((mel > 12).mean()), 1),
        'notes répétées %': round(100 * float((mel == 0).mean()), 1),
        'tonalité': f"{names[best[1]]} {best[2]} (r={best[0]:.2f})",
        'frappes muettes %': round(100 * muted / len(keys), 1),
    }


def render(cfg, out_path, text=TEXT, seed=0):
    files = {int(os.path.basename(f)[:2]) + 20: f for f in glob.glob(f'{REPO}/sounds/piano/*.wav')}
    for name, m in SIMPLE.items():
        files.setdefault(m, f'{REPO}/sounds/{name}')
    cache, sr = {}, 44100
    tl = timeline(to_keys(text), seed)
    buf = np.zeros(int((tl[-1][0] + 2.5) * sr))
    for t, k in tl:
        if k not in cfg:
            continue
        m = cfg[k]
        if m not in cache:
            cache[m] = read_wav(files[m])[0]
        x = cache[m]
        i = int(t * sr)
        buf[i:i + len(x)] += x[:len(buf) - i]
    buf *= 0.89 / np.max(np.abs(buf))
    pcm = (buf * 32767).astype('<i2')
    with open(out_path, 'wb') as f:
        f.write(b'RIFF' + struct.pack('<I', 36 + 2 * len(pcm)) + b'WAVEfmt '
                + struct.pack('<IHHIIHH', 16, 1, 1, sr, 2 * sr, 2, 16)
                + b'data' + struct.pack('<I', 2 * len(pcm)) + pcm.tobytes())


if __name__ == '__main__':
    if sys.argv[1] == '--render':
        render(load_config(sys.argv[3]), sys.argv[2])
    else:
        for path in sys.argv[1:]:
            print(os.path.basename(path), evaluate(load_config(path)))
