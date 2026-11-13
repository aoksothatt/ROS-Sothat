with open('extracted/Payload/client.app/client', 'rb') as f:
    data = f.read()

def get_str(va):
    off = va - 0x100000000
    if 0 <= off < len(data):
        end = data.find(b'\x00', off)
        return data[off:end].decode('latin1', errors='replace')
    return ''

print("Interface name at 0x10309d2d9:", get_str(0x10309d2d9))

# Let's read string references from 0x10309d2d0 to 0x10309d600
pos = 0x10309d2d9 - 0x100000000
for s in data[pos:pos+0x300].split(b'\x00'):
    if s:
        print("  String:", repr(s.decode('latin1', errors='replace')))
