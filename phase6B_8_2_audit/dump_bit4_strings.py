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

for va in [0x1030a3411, 0x1030a348b]:
    print(f"0x{va:08x}: {get_cstring(va)}")
