import struct
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

key = b'!@e}a6^C0dw5q4SW'
cipher = Cipher(algorithms.AES(key), modes.ECB())

with open(r'extracted\Payload\client.app\script.npk', 'rb') as f:
    f.seek(51366299)
    raw = f.read(3924)

# Skip 4-byte length prefix
cipher_data = raw[4:]
n_blocks = len(cipher_data) // 16
decryptor = cipher.decryptor()
plain = decryptor.update(cipher_data[:n_blocks*16])

print(f'Decrypted redirect.nxs length: {len(plain)}')
with open('redirect_decrypted.bin', 'wb') as f:
    f.write(plain)

# Let's inspect strings inside plain
import re
strings = re.findall(rb'[\x20-\x7e]{3,}', plain)
print(f'Found {len(strings)} strings in redirect.nxs:')
for s in strings:
    print('  ', s.decode('latin1'))
