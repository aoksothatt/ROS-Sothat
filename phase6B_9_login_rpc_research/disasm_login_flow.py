import struct
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM

CLIENT_PATH = "extracted/Payload/client.app/client"

with open(CLIENT_PATH, "rb") as f:
    data = f.read()

def disasm_range(start_vm, count):
    md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
    md.detail = True
    off = start_vm - 0x100000000
    code = data[off : off + count * 4]
    insns = list(md.disasm(code, start_vm))
    return insns

def read_cstr(vmaddr):
    off = vmaddr - 0x100000000
    end = data.find(b"\x00", off)
    return data[off:end].decode("latin1", errors="replace")

# Let's inspect from 0x1008a8100 to 0x1008a8450
insns = disasm_range(0x1008a8150, 150)
for insn in insns:
    # Check for string references (adrp + add/ldr)
    extra = ""
    print(f"0x{insn.address:08x}:  {insn.mnemonic:<8} {insn.op_str}")
