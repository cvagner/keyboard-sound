"""Lecture WAV PCM 16/24/32 bits et float 32/64 bits, en mono float64."""
import struct

import numpy as np


def read_wav(path):
    data = open(path, 'rb').read()
    assert data[:4] == b'RIFF' and data[8:12] == b'WAVE', path
    pos, fmt, samples = 12, None, None
    while pos + 8 <= len(data):
        cid, size = data[pos:pos + 4], struct.unpack('<I', data[pos + 4:pos + 8])[0]
        body = data[pos + 8:pos + 8 + size]
        if cid == b'fmt ':
            tag, ch, sr, _, _, bits = struct.unpack('<HHIIHH', body[:16])
            if tag == 0xFFFE:  # WAVE_FORMAT_EXTENSIBLE : sous-format dans le GUID
                tag = struct.unpack('<H', body[24:26])[0]
            fmt = (tag, ch, sr, bits)
        elif cid == b'data':
            samples = body
        pos += 8 + size + (size & 1)
    tag, ch, sr, bits = fmt
    if tag == 3:
        x = np.frombuffer(samples, dtype='<f4' if bits == 32 else '<f8').astype(np.float64)
    elif bits == 24:
        b = np.frombuffer(samples[:len(samples) // 3 * 3], dtype=np.uint8).reshape(-1, 3)
        x = (b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8) | (b[:, 2].astype(np.int8).astype(np.int32) << 16)) / 2 ** 23
    else:
        x = np.frombuffer(samples, dtype={16: '<i2', 32: '<i4'}[bits]) / float(2 ** (bits - 1))
    x = x[:len(x) // ch * ch].reshape(-1, ch).mean(axis=1)
    return x, sr, fmt
