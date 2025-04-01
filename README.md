# Keyboard sound

Production de sons lors de la frappe au clavier (configurable).

Inspiré par https://github.com/fgheng/keysound dont les sons proviennent (répertoire [audio/piano](https://github.com/fgheng/keysound/tree/master/audio/piano)).

Librairies :
* [`play-sound`](https://github.com/shime/play-sound) pour jouer les sons.
* [`node-global-key-listener`](https://github.com/LaunchMenu/node-global-key-listener) pour la détection de frappe (⚠ n'est plus maintenue depuis le 19/07/2024).

Solution testée avec :
* Linux
* Mac : rendre exécutable le script `node_modules/.../????`.
* Windows avec gitbash et powershell : installer un lecteur sans interface graphique (ex : `mplayer` dans le PATH)

Installation :
```sh
npm install
# ou
# npm ci
```

L'application demande une autorisation.

Exemples d'exécution :
```sh
# ./config/piano.json par défaut
node index.js

CONFIG_FILE=./config/piano.json node index.js
CONFIG_FILE=./config/piano-harmonie.json node index.js
CONFIG_FILE=./config/piano-harmonie2.json node index.js
CONFIG_FILE=./config/piano-lettre-a-elise.json node index.js

# Préciser le lecteur à utiliser (ici mplayer)
PLAYER="mplayer" node index.js
```

Cetains fichiers de configuration ont été produits avec l'aide d'une IA (ceci explique cela !) :
* piano : touches numériques puis `azerty`... `qsdfgh`... `wxcvbn`...
* harmonie : au regard de la langue française
* Lettre à Elise : en tapant les touches "azertyuiopqsdfghjklmwxcvbn"

Exemple de prompt :
```
J'utilise mon clavier azerty pour produire des sons à chaque frappe. Actuellement, les sons associés à la frappe sont configurés dans le fichier json qui suit. Peux-tu proposer une association différente, qui rendrait plus harmonieuse l'écoute des sons produits lors de la saisie d'un texte rédigé dans la langue française ?

+ contenu d'un des fichiers config/*json
```

J'espère que ç*a va* plaire !