import struct

macho_path = r'extracted\Payload\client.app\client'
with open(macho_path, 'rb') as f:
    client_data = f.read()

# Find section containing VA 0x102bebbac
# Mach-O header
ncmds = struct.unpack('<I', client_data[16:20])[0]
offset = 32
sections = []
for _ in range(ncmds):
    cmd, cmdsz = struct.unpack('<II', client_data[offset:offset+8])
    if cmd == 0x19:
        nsects = struct.unpack('<I', client_data[offset+64:offset+68])[0]
        sect_offset = offset + 72
        for s in range(nsects):
            s_sectname = client_data[sect_offset:sect_offset+16].rstrip(b'\x00').decode('latin1')
            s_segname = client_data[sect_offset+16:sect_offset+32].rstrip(b'\x00').decode('latin1')
            s_addr, s_size, s_offset = struct.unpack('<QQI', client_data[sect_offset+32:sect_offset+52])
            sections.append((s_segname, s_sectname, s_addr, s_size, s_offset))
            sect_offset += 80
    offset += cmdsz

tbl_va = 0x102bebbac
tbl_sec = [s for s in sections if s[2] <= tbl_va < s[2] + s[3]][0]
tbl_off = tbl_sec[4] + (tbl_va - tbl_sec[2])

print(f"Table VA: 0x{tbl_va:x} in {tbl_sec[0]}:{tbl_sec[1]} at file offset 0x{tbl_off:x}")

# Read 201 uint16 entries
# Base branch target = 0x101cd8d84
base_branch = 0x101cd8d84
default_target = 0x101cdd9e0

handlers = {}
for i in range(201):
    opcode = i + 3
    off_bytes = client_data[tbl_off + i*2 : tbl_off + (i+1)*2]
    offset_val = struct.unpack('<H', off_bytes)[0]
    dest_va = base_branch + (offset_val << 2)
    handlers[opcode] = dest_va

print(f"Total opcodes mapped: {len(handlers)}")
unique_handlers = set(handlers.values())
print(f"Unique target addresses: {len(unique_handlers)} (Default/invalid: 0x{default_target:x})")

valid_ops = {op: va for op, va in handlers.items() if va != default_target}
print(f"Valid implemented opcodes: {len(valid_ops)}")
for op in sorted(valid_ops.keys())[:20]:
    print(f"  Opcode {op:3d} (0x{op:02x}) -> 0x{valid_ops[op]:x}")
