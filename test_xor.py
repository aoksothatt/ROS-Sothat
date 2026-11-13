with open(r'extracted\Payload\client.app\script.npk', 'rb') as f:
    f.seek(51671674)
    entries = []
    for i in range(3983):
        import struct
        entry = f.read(28)
        id_val, off, zsize, size, zcrc, crc = struct.unpack('<IIIIII', entry[:24])
        entries.append((id_val, off, zsize, size, i))

# Find the two 74-byte entries: #1477 and #2668
e1 = [e for e in entries if e[4] == 1477][0]
e2 = [e for e in entries if e[4] == 2668][0]

with open(r'extracted\Payload\client.app\script.npk', 'rb') as f:
    f.seek(e1[1])
    c1 = f.read(e1[2])
    f.seek(e2[1])
    c2 = f.read(e2[2])

print('len(c1):', len(c1), 'len(c2):', len(c2))
xor_diff = bytes(a ^ b for a, b in zip(c1, c2))
print('Number of identical leading bytes:', next(i for i, b in enumerate(xor_diff) if b != 0))
print('xor_diff hex:', xor_diff.hex())
