---
name: config-harmonieuse
description: Démarche et outils pour produire, ajuster ou évaluer une configuration de sons (config/*.json) harmonieuse pour la frappe de texte en français sur clavier AZERTY. À utiliser pour créer une nouvelle config « harmonie », modifier piano-harmonie3.json, comparer des configs entre elles ou générer une démo audio.
---

# Configurations harmonieuses

`config/piano-harmonie3.json` a été produit par optimisation, pas à la main. Ce skill décrit la démarche et fournit les scripts (`scripts/`) qui le regénèrent à l'identique.

## Principes

1. **Les notes se superposent.** Chaque échantillon dure ~1,6 s ; à 6 frappes/s, 8 à 12 notes sonnent ensemble. L'harmonie se joue donc sur le nuage de notes simultanées, pas seulement sur l'enchaînement de deux notes.
2. **Gamme pentatonique de do** (do ré mi sol la) pour toutes les touches : aucune combinaison ne produit de demi-ton ni de triton, donc 0 % de dissonance dure quel que soit le texte.
3. **Touches physiques.** Les clés de config sont les positions QWERTY émises par `node-global-key-listener` (voir CLAUDE.md). Le texte français est converti en frappes AZERTY réelles (`scripts/corpus.py`) : `a`→`q`, `é`→`2`, `,`→`m`, `.`→`comma` (avec Maj), `ê`→`square bracket open` puis `e` (touche morte)…
4. **Notes imposées pour leur sens** (`FIXED` dans `optimize.py`) :
   - espace → do3 : basse de tonique à chaque mot ;
   - entrée → do2 : fin de paragraphe ;
   - `.` `;` (`comma`) → do4 : cadence (puis l'espace descend sur do3) ;
   - `,` `?` (`m`) → sol4 : dominante, suspension ou question ;
   - `:` (`dot`) → ré5 : degré instable, annonce ;
   - `!` (`forward slash`) → do5 : tonique éclatante.
5. **Optimisation des autres touches** par recuit simulé, sur les notes pentatoniques de sol3 à do6, en minimisant une somme pondérée de :

| Terme | Rôle |
|---|---|
| `rough` | rugosité psychoacoustique (Plomp-Levelt / Sethares, 6 harmoniques) des notes qui sonnent ensemble, pondérée par la décroissance (τ = 0,55 s) et la co-présence réelle des touches |
| `leap` | contour mélodique : sauts > quinte pénalisés, deux lettres différentes sur la même note aussi (monotonie) |
| `stab` | lettres fréquentes sur des degrés stables (do < sol < mi < la < ré) |
| `end` | fins de mot sur des degrés stables |
| `spread` | indice de Herfindahl : utiliser toute la gamme |
| `reg` | rester dans le registre médium |

Poids retenus pour harmonie3 : `W=1.0,1.0,0.4,0.6,4.0,0.1`, `REPEAT=0.8`. Des poids plus faibles sur `spread` et `leap` (`W=1.0,0.6,0.5,0.6,2.0,0.08`, `REPEAT=0.35`) donnent une variante plus douce (rugosité 0,65 au lieu de 0,92) mais monotone : quasi uniquement l'accord de do majeur, 13,7 % de notes répétées. Elle a été jugée moins bonne à l'écoute.

## Données

- **Corpus** : pages d'aide GNOME en français (`/usr/share/help/fr/**/*.page`, paquet `gnome-user-docs-fr`), ~1 million de frappes. Prose technique, d'où une validation sur un texte littéraire distinct (`TEXT` dans `evaluate.py`).
- **Échantillons** : `sounds/piano/NN-*.wav` = note MIDI NN+20 (vérifié par analyse spectrale de 14 à 79 ; aux extrêmes, la méthode se trompe d'harmonique). `sounds/a.wav`…`g.wav` = do4…si4 naturels. Un fichier est en float 32 bits (format WAV 3), d'où `scripts/wavio.py`, le module `wave` ne le lisant pas.

## Utilisation

Prérequis : `python3` avec `numpy`. Lancer sans `python3 -I` (les scripts s'importent entre eux).

```sh
S=.claude/skills/config-harmonieuse/scripts

# Regénère piano-harmonie3.json à l'identique (~1 min)
OUT=config/piano-harmonie3.json python3 $S/optimize.py 6

# Variante : autres poids
W=1.0,0.6,0.5,0.6,2.0,0.08 REPEAT=0.35 OUT=/tmp/variante.json python3 $S/optimize.py 6

# Comparer des configs (KPS = frappes par seconde)
python3 $S/evaluate.py config/piano-harmonie.json config/piano-harmonie3.json
KPS=9 python3 $S/evaluate.py config/piano-harmonie3.json

# Démo audio du texte d'évaluation
python3 $S/evaluate.py --render /tmp/demo.wav config/piano-harmonie3.json && paplay /tmp/demo.wav
```

Pour changer de tonalité ou de gamme : `CANDIDATES` et `FIXED` (optimize.py), `INSTAB` (model.py). Pour une autre disposition de clavier : `AZ` et `CHAR_KEYS` (corpus.py).

## Résultats de référence (texte littéraire, 6 frappes/s)

| Config | Dissonances dures | Rugosité | Sauts > octave | Frappes muettes |
|---|---|---|---|---|
| piano.json | 23,1 % | 1,04 | 46 % | 17 % |
| piano-harmonie.json | 17,9 % | 0,96 | 36 % | 18 % |
| piano-harmonie2.json | 14,8 % | 1,39 | 0 % | 18 % |
| piano-harmonie3.json | 0 % | 0,92 | 8 % | 0 % |

L'écart de rugosité est modeste, alors que harmonie3 fait aussi sonner l'espace. Le gain décisif est l'absence de dissonance dure. Le classement reste le même à 4 et à 9 frappes/s.

## Limites

- La table caractère AZERTY → touche physique suit la disposition xkb `fr` de mémoire, sans vérification sur le système.
- `œ` est compté comme `o` + `e` ; les caractères accessibles avec AltGr sont approximatifs ; les caractères avec Maj (`?`, `.`) prennent la note de leur touche.
- Les modèles de décroissance et de rugosité sont des approximations : l'écoute (démo audio) reste le juge final.
