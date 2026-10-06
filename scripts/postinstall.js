// Rend exécutables les serveurs de touches de node-global-key-listener :
// npm les installe sans le bit x, et la bibliothèque tente alors un
// chmod via sudo-prompt, qui plante avec Node >= 23 (util.isObject supprimé).
const fs = require('fs');
const path = require('path');

const binDir = path.join(path.dirname(require.resolve('node-global-key-listener/package.json')), 'bin');

for (const server of ['X11KeyServer', 'MacKeyServer']) {
  const serverPath = path.join(binDir, server);
  fs.chmodSync(serverPath, fs.statSync(serverPath).mode | 0o111);
}
