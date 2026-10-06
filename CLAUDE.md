# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Projet

Script Node.js (CommonJS, sans framework : `index.js`, `evdev.js`, `scripts/postinstall.js`) qui joue un son à chaque frappe au clavier, de façon globale (hors du terminal). Projet et documentation en français : garder les messages console et la documentation en français. Commits au format Conventional Commits, rédigés en français (`fix(config): …`, `feat: …`, `docs: …`).

## Commandes

```sh
npm ci                     # installation (+ postinstall : bit x des serveurs de touches)
npm start                  # = node . (config par défaut ./config/piano.json)
CONFIG_FILE=./config/piano-harmonie3.json node index.js
PLAYER=mplayer node index.js   # forcer le lecteur audio utilisé par play-sound
KEYBOARD_DEVICE=/dev/input/event2 node index.js   # forcer evdev (liste séparée par des virgules)

# Vérifier le démarrage sans jouer de son
PLAYER=true timeout 3 node index.js
```

Il n'y a ni tests (`npm test` échoue volontairement), ni linter, ni étape de build. Pour tester evdev sans accès au clavier, pointer `KEYBOARD_DEVICE` vers un FIFO alimenté en `struct input_event` (24 octets sur 64 bits : timeval, type u16, code u16, value s32).

## Architecture

- `index.js` charge un fichier JSON (`CONFIG_FILE`, chemin relatif au répertoire courant), reçoit les appuis de touche, passe le nom en minuscules et, s'il est une clé de la configuration, joue `sounds/<valeur>` via `play-sound` (chemin résolu depuis `__dirname`).
- Deux sources d'appuis : `evdev.js` lit directement `/dev/input/event*` si `KEYBOARD_DEVICE` est défini, ou sous Wayland quand un clavier (`/dev/input/by-{path,id}/*-event-kbd`) est lisible ; sinon `node-global-key-listener`. evdev réutilise la table `X11GlobalKeyLookup` de la bibliothèque (indexée par code clavier Linux), d'où des noms de touches identiques dans les deux modes. La répétition automatique est ignorée en evdev.
- `config/*.json` : objet plat `{ "<nom de touche>": "<chemin relatif à sounds/>" }`, par exemple `"q": "piano/42-D-小字1组.wav"`. Ajouter une configuration ne demande aucune modification du code.
- `config/piano-harmonie3.json` est **généré** (gamme pentatonique, optimisation sur un corpus français) : ne pas l'éditer à la main, passer par le skill `config-harmonieuse` (`.claude/skills/config-harmonieuse/`), dont les scripts le regénèrent à l'identique et permettent d'évaluer ou comparer des configs et de produire une démo audio.
- `sounds/piano/` : 88 notes numérotées (`NN-<note>-<octave>.wav`, noms d'octave en chinois hérités de [fgheng/keysound](https://github.com/fgheng/keysound)). `sounds/a.wav`…`g.wav` (notes simples à la racine) sont utilisés par `piano-harmonie2.json`.

### Noms de touches (piège)

Dans les deux modes, le nom de touche est le `standardName` de la table `X11GlobalKeyLookup` (vérifié dans `build/ts/X11KeyServer.js` et `build/ts/_data/X11GlobalKeyLookup.js` de la v0.3.0) :

- il correspond à la **position physique QWERTY**, indépendamment de la disposition du clavier : sur un clavier AZERTY, la touche marquée « A » émet `Q` ;
- la ponctuation est nommée en toutes lettres : `SEMICOLON`, `QUOTE`, `BACKTICK`, `COMMA`, `DOT`, `MINUS`, `EQUALS`…, donc `semicolon`, `quote`, etc. une fois en minuscules.

Les clés de `config/*.json` sont donc des positions physiques QWERTY en minuscules (`q`, `semicolon`, `forward slash`, `square bracket open`…), jamais des caractères. Pour une configuration pensée en AZERTY, convertir chaque caractère vers sa touche physique (`a`→`q`, `m`→`semicolon`, `é`→`2`, `ù`→`quote`, `,`→`m`…). Les caractères obtenus avec Maj (`.`, `?`) ou une touche morte (`ê`, `ô`…) n'ont pas de touche propre et ne peuvent pas être associés à un son distinct.

## Contraintes de plateforme

- `node-global-key-listener` n'est plus maintenue (depuis le 19/07/2024) et lance un binaire natif par OS (`node_modules/node-global-key-listener/bin/X11KeyServer`, `MacKeyServer`, `WinKeyServer.exe`). npm installe ces binaires sans le bit x : `scripts/postinstall.js` le rétablit. Sans lui, la bibliothèque tente un `chmod` via `sudo-prompt`, qui plante avec les Node récents (`util.isObject` absent, constaté en v24.21.0).
- Sous Wayland, `X11KeyServer` ne voit que les frappes destinées aux applications XWayland, d'où le mode evdev. Les claviers sont en `root:input` (660) : documenter l'accès temporaire par `setfacl` (README ; écrire `"u:${USER}:r"`, car en zsh `$USER:r` applique le modificateur `:r`), ne jamais présenter l'ajout au groupe `input` comme correctif par défaut (toutes les frappes deviennent lisibles par tout processus de l'utilisateur).
- `play-sound` délègue à un lecteur en ligne de commande présent dans le `PATH` ; sous Windows, en installer un sans interface graphique (ex. `mplayer`).
