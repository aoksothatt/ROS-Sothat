import struct
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

key = b'!@e}a6^C0dw5q4SW'
cipher = Cipher(algorithms.AES(key), modes.ECB())

with open(r'extracted\Payload\client.app\script.npk', 'rb') as f:
    f.seek(51671674)
    entries = []
    for i in range(3983):
        entry = f.read(28)
        id_val, off, zsize, size, zcrc, crc = struct.unpack('<IIIIII', entry[:24])
        entries.append((id_val, off, zsize, size, i))

print(f'Checking {len(entries)} entries for redirect.nxs...')
found = []
for id_val, off, zsize, size, idx in entries:
    if size < 20:
        continue
    with open(r'extracted\Payload\client.app\script.npk', 'rb') as f:
        f.seek(off)
        data = f.read(size)
    
    # Try 1: with 4-byte length prefix
    cipher_data = data[4:]
    n_blocks = len(cipher_data) // 16
    if n_blocks > 0:
        decryptor = cipher.decryptor()
        plain = decryptor.update(cipher_data[:n_blocks*16])
        if plain.startswith(b'c') or plain.startswith(b'\x03\xf3') or b'<module>' in plain or b'rotor' in plain:
            print(f'MATCH WITH 4-BYTE PREFIX! Entry #{idx} ID=0x{id_val:08x} off={off} size={size}:')
            print('  Preview:', plain[:60])
            found.append((idx, id_val, off, size, 4, plain))
            continue
            
    # Try 2: without 4-byte length prefix
    n_blocks = len(data) // 16
    if n_blocks > 0:
        decryptor = cipher.decryptor()
        plain = decryptor.update(data[:n_blocks*16])
        if plain.startswith(b'c') or plain.startswith(b'\x03\xf3') or b'<module>' in plain or b'rotor' in plain:
            print(f'MATCH WITHOUT PREFIX! Entry #{idx} ID=0x{id_val:08x} off={off} size={size}:')
            print('  Preview:', plain[:60])
            found.append((idx, id_val, off, size, 0, plain))

print(f'Done. Total matches: {len(found)}')
