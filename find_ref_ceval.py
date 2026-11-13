import struct

macho_path = r'extracted\Payload\client.app\client'
with open(macho_path, 'rb') as f:
    client_data = f.read()

# Parse sections
ncmds = struct.unpack('<I', client_data[16:20])[0]
offset = 32
sections = []
for _ in range(ncmds):
    cmd, cmdsz = struct.unpack('<II', client_data[offset:offset+8])
    if cmd == 0x19: # LC_SEGMENT_64
        nsects = struct.unpack('<I', client_data[offset+64:offset+68])[0]
        sect_offset = offset + 72
        for s in range(nsects):
            s_sectname = client_data[sect_offset:sect_offset+16].rstrip(b'\x00').decode('latin1')
            s_segname = client_data[sect_offset+16:sect_offset+32].rstrip(b'\x00').decode('latin1')
            s_addr, s_size, s_offset = struct.unpack('<QQI', client_data[sect_offset+32:sect_offset+52])
            sections.append((s_segname, s_sectname, s_addr, s_size, s_offset))
            sect_offset += 80
    offset += cmdsz

target_off = 0x31c2648
target_addr = None
for seg, sect, addr, size, off in sections:
    if off <= target_off < off + size:
        target_addr = addr + (target_off - off)
        print(f"String 0x{target_off:x} is in {seg}:{sect} at VA 0x{target_addr:x}")
        break

# Now search for ADRP + ADD pointing to target_addr
# ADRP page = target_addr & ~0xfff
# target page offset = target_addr & 0xfff
target_page = target_addr & ~0xfff
target_page_off = target_addr & 0xfff

print(f"Target page: 0x{target_page:x}, Page offset: 0x{target_page_off:x}")

text_sec = [s for s in sections if s[1] == '__text'][0]
text_seg, text_name, text_addr, text_size, text_off = text_sec
print(f"__text: VA 0x{text_addr:x} .. 0x{text_addr+text_size:x}, off 0x{text_off:x} .. 0x{text_off+text_size:x}")

text_bytes = client_data[text_off:text_off+text_size]
for i in range(0, text_size - 4, 4):
    w = struct.unpack('<I', text_bytes[i:i+4])[0]
    # Check if ADRP
    if (w & 0x9f000000) == 0x90000000:
        # Decode ADRP
        immlo = (w >> 29) & 3
        immhi = (w >> 5) & 0x7ffff
        imm = (immhi << 2) | immlo
        if imm & (1 << 20):
            imm -= (1 << 21)
        ins_addr = text_addr + i
        page = (ins_addr & ~0xfff) + (imm << 12)
        if page == target_page:
            # Check next instruction for ADD with target_page_off
            next_w = struct.unpack('<I', text_bytes[i+4:i+8])[0]
            # ADD (immediate): (w & 0xffc00000) == 0x91000000
            if (next_w & 0xff800000) == 0x91000000:
                imm12 = (next_w >> 10) & 0xfff
                if imm12 == target_page_off:
                    print(f"MATCH! Referenced at VA 0x{ins_addr:x} (offset 0x{text_off+i:x})")
