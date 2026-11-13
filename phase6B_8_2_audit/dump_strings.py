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

for va in [0x1030a2d6c, 0x1030a2db5, 0x1030a2e00, 0x1030a2e48, 0x1030a2e95, 0x1030a33b3]:
    print(f"0x{va:08x}: {get_cstring(va)}")
