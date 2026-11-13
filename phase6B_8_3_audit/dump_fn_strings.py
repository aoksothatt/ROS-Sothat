BINARY_PATH = "extracted/Payload/client.app/client"

def get_cstring(va):
    with open(BINARY_PATH, "rb") as f:
        f.seek(va - 0x100000000)
        s = bytearray()
        while True:
            b = f.read(1)
            if not b or b == b'\x00':
                break
            s.extend(b)
    return s.decode('latin1', errors='replace')

for va in [0x1030a3fc2, 0x1031c0f21, 0x1030a4162, 0x103093da2]:
    print(f"0x{va:08x}: {get_cstring(va)}")
