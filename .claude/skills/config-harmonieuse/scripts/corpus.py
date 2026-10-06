"""Corpus français (aide GNOME en français) et traduction en suite de touches
physiques d'un clavier AZERTY (xkb fr, Linux), avec les noms émis par
node-global-key-listener (standardName en minuscules)."""
import glob
import re
import unicodedata
import xml.etree.ElementTree as ET

SKIP_TAGS = {'code', 'cmd', 'input', 'output', 'screen', 'sys', 'file', 'key', 'keyseq',
             'credit', 'license', 'info', 'media', 'app', 'email', 'name', 'years'}
BLOCK_TAGS = {'p', 'title', 'item', 'td', 'desc', 'subtitle'}


def _text(el, out):
    tag = el.tag.split('}')[-1]
    if tag in SKIP_TAGS:
        return
    if el.text:
        out.append(el.text)
    for child in el:
        _text(child, out)
        if child.tail:
            out.append(child.tail)


def load_corpus():
    paras = []
    for path in sorted(glob.glob('/usr/share/help/fr/**/*.page', recursive=True)):
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            continue
        for el in root.iter():
            if el.tag.split('}')[-1] in BLOCK_TAGS:
                out = []
                _text(el, out)
                t = re.sub(r'\s+', ' ', ''.join(out)).strip()
                if len(t) > 40 and not re.search(r'[A-Za-z]+\.[a-z]{2,4}\b|https?:', t):
                    paras.append(t)
    return paras


# Touches physiques (noms node-global-key-listener) pour un caractère tapé en AZERTY fr.
# Majuscules et chiffres : même touche que la minuscule / le caractère de base (Maj muet).
AZ = {'a': 'q', 'q': 'a', 'z': 'w', 'w': 'z', 'm': 'semicolon'}
CHAR_KEYS = {
    'é': ['2'], 'è': ['7'], 'ç': ['9'], 'à': ['0'], 'ù': ['quote'],
    '&': ['1'], '"': ['3'], "'": ['4'], '’': ['4'], '(': ['5'], '-': ['6'], '_': ['8'],
    ')': ['minus'], '=': ['equals'], '°': ['minus'], '+': ['equals'],
    '1': ['1'], '2': ['2'], '3': ['3'], '4': ['4'], '5': ['5'],
    '6': ['6'], '7': ['7'], '8': ['8'], '9': ['9'], '0': ['0'],
    ',': ['m'], '?': ['m'], ';': ['comma'], '.': ['comma'], ':': ['dot'], '/': ['dot'],
    '!': ['forward slash'], '§': ['forward slash'], '*': ['backslash'], '$': ['square bracket close'],
    '%': ['quote'], '<': [], '>': [],
    '«': ['w'], '»': ['x'],  # AltGr+z / AltGr+x
    ' ': ['space'], ' ': ['space'], ' ': ['space'], '\n': ['return'],
}
DEAD_CIRC = 'square bracket open'  # ^ (et ¨ avec Maj) : touche morte


def char_to_keys(c):
    lc = c.lower()
    if lc in CHAR_KEYS:
        return CHAR_KEYS[lc]
    if 'a' <= lc <= 'z':
        return [AZ.get(lc, lc)]
    if lc in 'œ':
        return ['o', 'e']
    base = unicodedata.normalize('NFD', lc)
    if len(base) == 2 and base[1] in '̂̈' and 'a' <= base[0] <= 'z':
        return [DEAD_CIRC, AZ.get(base[0], base[0])]
    return None


def to_keys(text):
    keys = []
    for c in text:
        k = char_to_keys(c)
        if k is None:
            continue
        keys.extend(k)
    return keys
