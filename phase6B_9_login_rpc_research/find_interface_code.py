import struct

with open('extracted/Payload/client.app/client', 'rb') as f:
    data = f.read()

target_va = 0x1030a24eb # compressLength
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
            print(f"Hit ADRP at pc=0x{pc:x}")
