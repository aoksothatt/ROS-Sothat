with open('extracted/Payload/client.app/client', 'rb') as f:
    data = f.read()

import re

for pattern in [b'BaseAppLoginRequest', b'baseAddr', b'sending base app request']:
    for m in re.finditer(pattern, data):
        off = m.start()
        va = 0x100000000 + off
        line = data[off-20:off+60].split(b'\x00')[0]
        print(f"Pattern {pattern.decode()}: off=0x{off:x}, va=0x{va:x}: {repr(line)}")
