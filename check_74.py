import struct

# Load jump table
with open(r'extracted\Payload\client.app\client', 'rb') as f:
    f.seek(0x2bebbac)
    raw = f.read(201*2)

base = 0x101cd8d84
handlers = {}
for i in range(201):
    op = i + 3
    off = struct.unpack('<H', raw[i*2:(i+1)*2])[0]
    handlers[op] = base + (off << 2)

print("Handler for 74:", hex(handlers.get(74, 0)))
