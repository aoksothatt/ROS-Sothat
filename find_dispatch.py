import struct

with open(r'extracted\Payload\client.app\client', 'rb') as f:
    client_data = f.read()

# Search for B or B.cond or BR or jump tables pointing to 0x101cdd9e0
target_addr = 0x101cdd9e0
text_addr = 0x100007140
text_off = 0x7140
text_size = 0x287c18c - 0x7140

print("Searching for branches to 0x101cdd9e0 in ceval...")
# ceval is roughly around 0x101cd0000 to 0x101ce5000
start_search = 0x101cd0000
end_search = 0x101ce5000

start_idx = text_off + (start_search - text_addr)
end_idx = text_off + (end_search - text_addr)

for i in range(start_idx, end_idx, 4):
    curr_addr = text_addr + (i - text_off)
    w = struct.unpack('<I', client_data[i:i+4])[0]
    
    # B <imm26>: (w & 0xfc000000) == 0x14000000
    if (w & 0xfc000000) == 0x14000000:
        imm26 = w & 0x03ffffff
        if imm26 & (1 << 25): imm26 -= (1 << 26)
        dest = curr_addr + (imm26 << 2)
        if dest == target_addr:
            print(f"Unconditional B at 0x{curr_addr:x} -> 0x{target_addr:x}")

    # B.cond <imm19>: (w & 0xff000010) == 0x54000000
    if (w & 0xff000010) == 0x54000000:
        imm19 = (w >> 5) & 0x7ffff
        if imm19 & (1 << 18): imm19 -= (1 << 19)
        dest = curr_addr + (imm19 << 2)
        if dest == target_addr:
            print(f"B.cond at 0x{curr_addr:x} -> 0x{target_addr:x}")

    # CBZ / CBNZ <imm19>
    if (w & 0x7e000000) == 0x34000000:
        imm19 = (w >> 5) & 0x7ffff
        if imm19 & (1 << 18): imm19 -= (1 << 19)
        dest = curr_addr + (imm19 << 2)
        if dest == target_addr:
            print(f"CBZ/CBNZ at 0x{curr_addr:x} -> 0x{target_addr:x}")
