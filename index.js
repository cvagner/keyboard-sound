const { GlobalKeyboardListener } = require("node-global-key-listener");
const fs = require('fs');
const path = require('path');
const player = require('play-sound')({
  player: process.env.PLAYER
});

const configFile = process.env.CONFIG_FILE ? process.env.CONFIG_FILE : './config/piano.json';
console.log(`Configuration : ${configFile}`);
const config = JSON.parse(fs.readFileSync(configFile, 'utf-8'));
const keyBindings = config;

function playSound(note) {
  const soundPath = path.join(__dirname, 'sounds', `${note}`);
  player.play(soundPath, (err) => {
    if (err) console.error(`Erreur : ${err}`);
  });
}

const v = new GlobalKeyboardListener();

v.addListener(e => {
  if (e.state == 'DOWN') {
    if (!e.name) {
      return;
    }
    const key = e.name.toLowerCase();
    if (key in keyBindings) {
      const note = keyBindings[key];
      console.log(`  Touche "${key}" > son "${note}"`);
      playSound(note);
    }
  }
});

console.log('Écoute (globale)');

process.on('SIGINT', () => {
  console.log('Arrêt');
  v.kill();
  process.exit();
});
