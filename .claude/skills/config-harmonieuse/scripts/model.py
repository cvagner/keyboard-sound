"""Modèle d'écoute : notes qui se superposent pendant la frappe, rugosité
psychoacoustique (Sethares 1993), contour mélodique, stabilité tonale."""
import math
import os

import numpy as np

KPS = 6.0     # frappes par seconde (≈ 70 mots/min)
TAU = 0.55    # constante de décroissance perçue d'une note de piano (s)
MAX_LAG = 10  # au-delà, la note précédente est quasi éteinte
LAG_W = np.array([math.exp(-lag / KPS / TAU) for lag in range(1, MAX_LAG + 1)])

REPEAT = float(os.environ.get('REPEAT', 0.8))

N_HARM = 6
H_AMP = [0.88 ** k for k in range(N_HARM)]


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def _pl(f1, f2, a1, a2):
    """Dissonance de Plomp-Levelt paramétrée par Sethares."""
    s = 0.24 / (0.0207 * min(f1, f2) + 18.96)
    d = abs(f2 - f1)
    return min(a1, a2) * (math.exp(-3.51 * s * d) - math.exp(-5.75 * s * d))


def roughness(m1, m2):
    """Rugosité d'une paire de notes avec harmoniques (sans la rugosité propre de chaque note)."""
    total = 0.0
    for i in range(N_HARM):
        for j in range(N_HARM):
            total += _pl(hz(m1) * (i + 1), hz(m2) * (j + 1), H_AMP[i], H_AMP[j])
    return total


def leap_cost(d):
    d = abs(d)
    if d == 0:
        return REPEAT  # deux lettres différentes sur la même note : monotonie
    if d <= 5:
        return 0.0
    if d <= 7:
        return 0.1
    if d <= 9:
        return 0.3
    if d <= 12:
        return 0.5
    return 0.8 + 0.12 * (d - 12)


# Stabilité dans do majeur (instabilité 0 = repos)
INSTAB = {0: 0.0, 7: 0.15, 4: 0.2, 9: 0.45, 2: 0.55}
# Profil de Krumhansl-Kessler (majeur), pour mesurer la clarté tonale
KK_MAJOR = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
