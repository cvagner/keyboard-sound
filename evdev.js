// Écoute directe des claviers via evdev (/dev/input/event*), pour Wayland où
// node-global-key-listener ne voit que les applications XWayland.
const fs = require('fs');
const os = require('os');
const path = require('path');
// Table indexée par les codes clavier Linux (linux/input-event-codes.h) :
// on obtient les mêmes noms de touches qu'avec node-global-key-listener.
const { X11GlobalKeyLookup } = require('node-global-key-listener/build/ts/_data/X11GlobalKeyLookup');

// struct input_event : timeval (2 x long), type (u16), code (u16), value (s32)
const LONG_SIZE = process.arch.endsWith('64') ? 8 : 4;
const EVENT_SIZE = 2 * LONG_SIZE + 8;
const EV_KEY = 1;
const KEY_PRESS = 1; // 0 = relâchement, 2 = répétition automatique

function findKeyboards() {
  const devices = new Set();
  for (const dir of ['/dev/input/by-path', '/dev/input/by-id']) {
    let entries = [];
    try {
      entries = fs.readdirSync(dir);
    } catch (err) {
      continue;
    }
    for (const entry of entries) {
      if (entry.endsWith('-event-kbd')) {
        devices.add(fs.realpathSync(path.join(dir, entry)));
      }
    }
  }
  return [...devices];
}

function isReadable(device) {
  try {
    fs.accessSync(device, fs.constants.R_OK);
    return true;
  } catch (err) {
    return false;
  }
}

function listen(devices, onKeyDown) {
  const le = os.endianness() === 'LE';
  const streams = devices.map(device => {
    let pending = Buffer.alloc(0);
    const stream = fs.createReadStream(device);
    stream.on('data', chunk => {
      pending = Buffer.concat([pending, chunk]);
      let offset = 0;
      for (; offset + EVENT_SIZE <= pending.length; offset += EVENT_SIZE) {
        const base = offset + 2 * LONG_SIZE;
        const type = le ? pending.readUInt16LE(base) : pending.readUInt16BE(base);
        const code = le ? pending.readUInt16LE(base + 2) : pending.readUInt16BE(base + 2);
        const value = le ? pending.readInt32LE(base + 4) : pending.readInt32BE(base + 4);
        if (type === EV_KEY && value === KEY_PRESS && X11GlobalKeyLookup[code]) {
          onKeyDown(X11GlobalKeyLookup[code].standardName);
        }
      }
      pending = pending.subarray(offset);
    });
    stream.on('error', err => console.error(`Erreur clavier ${device} : ${err.message}`));
    return stream;
  });
  return () => streams.forEach(stream => stream.destroy());
}

module.exports = { findKeyboards, isReadable, listen };
