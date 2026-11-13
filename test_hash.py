import struct, zlib

def mmh3_hash(key, seed=0):
    key = bytearray(key.encode('utf-8') if isinstance(key, str) else key)
    length = len(key)
    nblocks = length // 4
    h1 = seed
    c1 = 0xcc9e2d51
    c2 = 0x1b873593
    for i in range(0, nblocks * 4, 4):
        k1 = struct.unpack('<I', key[i:i+4])[0]
        k1 = (k1 * c1) & 0xffffffff
        k1 = ((k1 << 15) | (k1 >> 17)) & 0xffffffff
        k1 = (k1 * c2) & 0xffffffff
        h1 ^= k1
        h1 = ((h1 << 13) | (h1 >> 19)) & 0xffffffff
        h1 = (h1 * 5 + 0xe6546b64) & 0xffffffff
    tail = key[nblocks * 4:]
    k1 = 0
    if len(tail) == 3:
        k1 ^= tail[2] << 16
    if len(tail) >= 2:
        k1 ^= tail[1] << 8
    if len(tail) >= 1:
        k1 ^= tail[0]
        k1 = (k1 * c1) & 0xffffffff
        k1 = ((k1 << 15) | (k1 >> 17)) & 0xffffffff
        k1 = (k1 * c2) & 0xffffffff
        h1 ^= k1
    h1 ^= length
    h1 ^= (h1 >> 16)
    h1 = (h1 * 0x85ebca6b) & 0xffffffff
    h1 ^= (h1 >> 13)
    h1 = (h1 * 0xc2b2ae35) & 0xffffffff
    h1 ^= (h1 >> 16)
    return h1

def fnv1a(s):
    h = 0x811c9dc5
    for b in (s.encode('utf-8') if isinstance(s, str) else s):
        h = ((h ^ b) * 0x01000193) & 0xffffffff
    return h

def djb2(s):
    h = 5381
    for b in (s.encode('utf-8') if isinstance(s, str) else s):
        h = (((h << 5) + h) + b) & 0xffffffff
    return h

def sdbm(s):
    h = 0
    for b in (s.encode('utf-8') if isinstance(s, str) else s):
        h = (b + (h << 6) + (h << 16) - h) & 0xffffffff
    return h

# Load all IDs from script.npk
with open(r'extracted\Payload\client.app\script.npk', 'rb') as f:
    f.seek(51671674)
    npk_ids = set()
    for _ in range(3983):
        entry = f.read(28)
        npk_ids.add(struct.unpack('<I', entry[:4])[0])

print(f'Loaded {len(npk_ids)} IDs from script.npk')

# Test candidates
paths = [
    'camera/camerarig.py', 'libclaudia/Classes/Animator.py', 'redirect.nxs',
    'setting.ini', 'neox.xml', 'script', 'main', 'main.py', '__init__.py'
]

hash_funcs = {
    'mmh3_0': lambda s: mmh3_hash(s, 0),
    'mmh3_9747': lambda s: mmh3_hash(s, 0x9747B28C),
    'crc32': lambda s: zlib.crc32(s.encode('utf-8')) & 0xffffffff,
    'fnv1a': fnv1a,
    'djb2': djb2,
    'sdbm': sdbm,
}

for p in paths:
    variants = [
        p, p.lower(), p.upper(),
        p.replace('.py', '.pyc'), p.replace('.py', '.nxs'),
        'script/' + p, 'script/' + p.replace('.py', '.nxs'),
        p.split('/')[-1], p.split('/')[-1].replace('.py', '.nxs'),
    ]
    for v in set(variants):
        for name, fn in hash_funcs.items():
            h = fn(v)
            if h in npk_ids:
                print(f'MATCH FOUND! {name}(\"{v}\") = 0x{h:08x}')
