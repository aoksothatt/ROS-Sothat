import struct

with open('extracted/Payload/client.app/client', 'rb') as f:
    data = f.read()

start_va = 0x1008a7000
end_va = 0x1008ab000

targets = {
    0x100917b18: "Bundle::startMessage",
    0x100917c04: "Bundle::startRequest",
    0x100917828: "Bundle::init/create",
    0x100917074: "Bundle::xxx",
}

for va in range(start_va, end_va, 4):
    off = va - 0x100000000
    inst = struct.unpack('<I', data[off:off+4])[0]
    # check BL instruction: bits 26..31 == 0b100101
    if (inst & 0xfc000000) == 0x94000000:
        imm26 = inst & 0x03ffffff
        if imm26 & 0x02000000:
            imm26 -= 0x04000000
        target = va + (imm26 << 2)
        if target in targets:
            print(f"Call to {targets[target]} at 0x{va:x}")
