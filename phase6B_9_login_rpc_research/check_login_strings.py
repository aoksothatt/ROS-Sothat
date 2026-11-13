import struct

with open('extracted/Payload/client.app/client', 'rb') as f:
    data = f.read()

def get_str(va):
    off = va - 0x100000000
    if 0 <= off < len(data):
        end = data.find(b'\x00', off)
        if end != -1:
            return data[off:end].decode('latin1', errors='replace')
    return ''

print("0x10309c09b:", repr(get_str(0x10309c09b)))
print("0x10309c0e5:", repr(get_str(0x10309c0e5)))
print("0x10309c120:", repr(get_str(0x10309c120)))
print("0x10309c15b:", repr(get_str(0x10309c15b)))
print("0x10309c17b:", repr(get_str(0x10309c17b)))
print("0x10309c1ef:", repr(get_str(0x10309c1ef)))
print("0x10309c1dc:", repr(get_str(0x10309c1dc)))
print("0x10309c24a:", repr(get_str(0x10309c24a)))
print("0x10309a000+0xf10 (0x10309af10):", repr(get_str(0x10309af10)))
