const fs = require('fs');
const path = require('path');
const evdev = require('./evdev');
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

function onKeyDown(name) {
  if (!name) {
    return;
  }
  const key = name.toLowerCase();
  if (key in keyBindings) {
    const note = keyBindings[key];
    console.log(`  Touche "${key}" > son "${note}"`);
    playSound(note);
  }
}

// Claviers evdev : KEYBOARD_DEVICE (liste séparée par des virgules) ou, sous Wayland, détection
function evdevKeyboards() {
  if (process.env.KEYBOARD_DEVICE) {
    const devices = process.env.KEYBOARD_DEVICE.split(',');
    const unreadable = devices.filter(device => !evdev.isReadable(device));
    if (unreadable.length) {
      console.error(`Clavier illisible : ${unreadable.join(', ')} (voir README, section Wayland)`);
      process.exit(1);
    }
    return devices;
  }
  if (process.env.XDG_SESSION_TYPE !== 'wayland') {
    return [];
  }
  const devices = evdev.findKeyboards();
  const readable = devices.filter(evdev.isReadable);
  if (!readable.length) {
    console.log(`Wayland : clavier illisible (${devices.join(', ') || 'aucun trouvé'}), seules les applications XWayland seront entendues (voir README, section Wayland)`);
  }
  return readable;
}

let stop;
const keyboards = evdevKeyboards();
if (keyboards.length) {
  stop = evdev.listen(keyboards, onKeyDown);
  console.log(`Écoute (evdev : ${keyboards.join(', ')})`);
} else {
  const { GlobalKeyboardListener } = require("node-global-key-listener");
  const v = new GlobalKeyboardListener();
  v.addListener(e => {
    if (e.state == 'DOWN') {
      onKeyDown(e.name);
    }
  });
  stop = () => v.kill();
  console.log('Écoute (globale)');
}

process.on('SIGINT', () => {
  console.log('Arrêt');
  stop();
  process.exit();
});
