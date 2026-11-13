import struct

with open('extracted/Payload/client.app/client', 'rb') as f:
    data = f.read()

target_va = 0x1030a1619
target_page = target_va >> 12

text_start = 0x7140
text_end = text_start + 0x287504c

print(f"Scanning for target_page 0x{target_page:x}...")
for off in range(text_start, text_end, 4):
    inst = struct.unpack('<I', data[off:off+4])[0]
    if (inst & 0x9f000000) == 0x90000000:
        rd = inst & 0x1f
        immlo = (inst >> 29) & 3
        immhi = (inst >> 5) & 0x7ffff
        imm = (immhi << 2) | immlo
        if imm & 0x100000:
            imm -= 0x200000
        pc = 0x100000000 + off
        pc_page = pc >> 12
        if pc_page + imm == target_page:
            # check next inst
            next_inst = struct.unpack('<I', data[off+4:off+8])[0]
            rn = (next_inst >> 5) & 0x1f
            if rn == rd and (next_inst & 0xff800000) == 0x91000000:
                imm12 = (next_inst >> 10) & 0xfff
                final_va = ((pc_page + imm) << 12) + imm12
                if abs(final_va - target_va) < 64:
                    print(f"Hit at pc=0x{pc:x} -> va=0x{final_va:x}")
