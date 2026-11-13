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

print(f"0x1030a1e08: {get_cstring(0x1030a1e08)}")
