import zipfile, capstone

with zipfile.ZipFile('RoS-Legacy-iOS.ipa') as z:
    client_data = z.read('Payload/client.app/client')

md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)

# Look for adrp loading page 0x1030af000 followed by add with 0x24d
# Page PC: target_page - (ins_addr & ~0xfff)
target_addr = 0x1029595d0
print('Searching for code references to 0x1029595d0...')

import struct
for off in range(0, 0x2959400, 4): # __text section
    ins_bytes = client_data[off:off+4]
    ins_val = struct.unpack('<I', ins_bytes)[0]
    # Check if adrp
    if (ins_val & 0x9f000000) == 0x90000000:
        immlo = (ins_val >> 29) & 3
        immhi = (ins_val >> 5) & 0x7ffff
        imm = (immhi << 2) | immlo
        if imm & 0x100000:
            imm -= 0x200000
        pc = 0x100000000 + off
        page = (pc & ~0xfff) + (imm << 12)
        if page == (target_addr & ~0xfff):
            # check next instruction
            next_bytes = client_data[off+4:off+8]
            next_val = struct.unpack('<I', next_bytes)[0]
            # check if add or ldr
            if (next_val & 0xffc00000) == 0x91000000: # add
                imm12 = (next_val >> 10) & 0xfff
                if imm12 == (target_addr & 0xfff):
                    print(f'Found reference at 0x{pc:x} (file off {hex(off)})')
