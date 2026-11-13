import struct
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM

CLIENT_PATH = "extracted/Payload/client.app/client"

with open(CLIENT_PATH, "rb") as f:
    data = f.read()

target = 0x1008992fc
filesize = len(data)

callers = []
for i in range(0, filesize - 4, 4):
    insn_val = struct.unpack_from("<I", data, i)[0]
    if (insn_val & 0xFC000000) == 0x94000000:
        imm26 = insn_val & 0x03FFFFFF
        if imm26 & 0x02000000:
            imm26 -= 0x04000000
        dest = 0x100000000 + i + (imm26 << 2)
        if dest == target:
            callers.append(0x100000000 + i)

print(f"Found {len(callers)} callers of LogOnParams::addToStream (0x{target:x}):")
for c in callers:
    print(f"  0x{c:08x}")
