BINARY_PATH = "extracted/Payload/client.app/client"

with open(BINARY_PATH, "rb") as f:
    f.seek(0x1030a2c00 - 0x100000000)
    data = f.read(0x1030a3800 - 0x1030a2c00)

offset = 0
while offset < len(data):
    if b"Nub" in data[offset:offset+100] or b"processFilteredPacket" in data[offset:offset+100]:
        end = data.find(b'\x00', offset)
        if end != -1:
            s = data[offset:end].decode('latin1', errors='replace')
            print(f"0x{0x1030a2c00 + offset:08x}: {s}")
            offset = end + 1
            continue
    offset += 1
