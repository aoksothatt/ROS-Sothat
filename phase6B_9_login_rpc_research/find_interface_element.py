with open('extracted/Payload/client.app/client', 'rb') as f:
    data = f.read()

import re

for pattern in [b'compressLength', b'expandLength', b'newMessage', b'handleMessage( %s )']:
    for m in re.finditer(pattern, data):
        off = m.start()
        va = 0x100000000 + off
        line = data[off-30:off+70].split(b'\x00')[0]
        print(f"Pattern {pattern.decode()}: off=0x{off:x}, va=0x{va:x}: {repr(line)}")
