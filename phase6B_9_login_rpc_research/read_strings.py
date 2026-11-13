import struct

CLIENT_PATH = "extracted/Payload/client.app/client"

with open(CLIENT_PATH, "rb") as f:
    data = f.read()

def read_cstr(vmaddr):
    off = vmaddr - 0x100000000
    end = data.find(b"\x00", off)
    return data[off:end].decode("latin1", errors="replace")

print("String at 0x10309abc0:", read_cstr(0x10309abc0))
print("String at 0x10309c254:", read_cstr(0x10309c254))
