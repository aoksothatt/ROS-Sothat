import struct

with open('extracted/Payload/client.app/client', 'rb') as f:
    data = f.read()

target_strs = [
    b'LoginHandler::handleMessage: Got reply of unexpected size',
    b'LoginHandler::onLoginReply',
    b'sending base app request',
    b'Unable to connect to BaseApp',
    b'ServerConnection::logOnBegin conneting',
    b'entities\\loginapp.pubkey'
]

targets = {}
for s in target_strs:
    pos = data.find(s)
    if pos != -1:
        va = 0x100000000 + pos
        targets[s] = (pos, va)
        print("Target: %s at off=0x%x, va=0x%x" % (s.decode('latin1', errors='replace'), pos, va))

text_start = 0x7140
text_end = text_start + 0x287504c

target_vas = {v[1]: k for k, v in targets.items()}
target_pages = {(v[1] >> 12): (v[1], k) for k, v in targets.items()}

print("Scanning __text for ADRP + ADD references...")
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
        target_page = pc_page + imm
        if target_page in target_pages:
            next_inst = struct.unpack('<I', data[off+4:off+8])[0]
            rn = (next_inst >> 5) & 0x1f
            if rn == rd:
                imm12 = (next_inst >> 10) & 0xfff
                if (next_inst & 0xff800000) == 0x91000000:
                    final_va = (target_page << 12) + imm12
                    for s_va, s_name in target_vas.items():
                        if abs(final_va - s_va) < 64:
                            print("Hit at pc=0x%x -> %s (va=0x%x)" % (pc, s_name.decode('latin1', errors='replace'), final_va))
