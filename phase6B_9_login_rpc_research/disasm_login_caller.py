import struct
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM

CLIENT_PATH = "extracted/Payload/client.app/client"

with open(CLIENT_PATH, "rb") as f:
    data = f.read()

# VM to file offset for __TEXT is vmaddr - 0x100000000
def disasm_range(start_vm, count):
    md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
    md.detail = True
    off = start_vm - 0x100000000
    code = data[off : off + count * 4]
    insns = list(md.disasm(code, start_vm))
    return insns

print("--- DISASSEMBLY AROUND 0x1008995b0 (Caller of PublicKeyCipher::encrypt) ---")
# Let's inspect from 0x100899450 to 0x100899700
insns = disasm_range(0x100899450, 120)
for insn in insns:
    print(f"0x{insn.address:08x}:  {insn.mnemonic:<8} {insn.op_str}")

print("\n--- DISASSEMBLY AROUND 0x1008ab4c4 (Caller of PublicKeyCipher::setKey) ---")
insns2 = disasm_range(0x1008ab400, 60)
for insn in insns2:
    print(f"0x{insn.address:08x}:  {insn.mnemonic:<8} {insn.op_str}")
