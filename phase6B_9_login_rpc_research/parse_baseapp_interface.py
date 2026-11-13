with open('extracted/Payload/client.app/client', 'rb') as f:
    data = f.read()

def get_str(va):
    off = va - 0x100000000
    if 0 <= off < len(data):
        end = data.find(b'\x00', off)
        return data[off:end].decode('latin1', errors='replace')
    return ''

# Let's inspect the names and parameters from the disassembly:
items = [
    # (pc, name_va, length_style, length_param)
    (0x1008cdeac, 0x10309d187, 1, 2), # baseAppLogin
    (0x1008cded0, 0x10309d194, 0, 4), # authenticate
    (0x1008cdef8, 0x10309d1a1, 0, 0x18), # avatarUpdateImplicit
    (0x1008cdf1c, 0x10309d1b6, 0, 0x20), # avatarUpdateExplicit
    (0x1008cdf40, 0x10309d1cb, 0, 0x18), # avatarUpdateWardImplicit
    (0x1008cdf64, 0x10309d1e4, 0, 0x20), # avatarUpdateWardExplicit
    (0x1008cdf88, 0x10309d1fd, 0, 0),    # switchInterface
    (0x1008cdfac, 0x10309d20d, 1, 2),    # requestEntityUpdate
    (0x1008cdfd0, 0x10309d221, 0, 8),    # enableEntities
    (0x1008cdff4, 0x10309d230, 0, 8),    # setSpaceViewportAck
    (0x1008ce018, 0x10309d244, 0, 8),    # setVehicleAck
    (0x1008ce03c, 0x10309d252, 0, 4),    # ?
    (0x1008ce060, 0x10309d263, 1, 2),    # ?
    (0x1008ce084, 0x10309d278, 1, 2),    # ?
    (0x1008ce0a8, 0x10309d28e, 1, 2),    # ?
    (0x1008ce0cc, 0x10309d2a7, 0, 1),    # ?
    (0x1008ce0f0, 0x10309d2b8, 0, 1),    # ?
    (0x1008ce118, 0x10309d2cb, 1, 2),    # ?
]

print("BaseAppExtInterface Message ID Map:")
for idx, item in enumerate(items):
    name = get_str(item[1])
    style_str = "FIXED" if item[2] == 0 else f"VAR({item[3]}B)"
    print(f"  ID 0x{idx:02x} ({idx:2d}): name={name:<25} style={style_str:<10} param={item[3]}")
