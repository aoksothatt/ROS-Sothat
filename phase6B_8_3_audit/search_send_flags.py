import capstone

BINARY_PATH = "extracted/Payload/client.app/client"

def search_constants():
    with open(BINARY_PATH, "rb") as f:
        # Search Mercury area: 0x100910000 - 0x100935000
        start_va = 0x100910000
        end_va = 0x100935000
        f.seek(start_va - 0x100000000)
        code = f.read(end_va - start_va)
        
    md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
    md.detail = True
    
    flag_values = [0x0001, 0x0002, 0x0004, 0x0008, 0x0010, 0x0020, 0x0040, 0x0080, 0x0100, 0x0200, 0x0400]
    
    print("Searching for flag immediate values in Mercury code...")
    for ins in md.disasm(code, start_va):
        if ins.mnemonic in ['mov', 'movz', 'orr', 'and', 'tst', 'cmp']:
            for op in ins.operands:
                if op.type == capstone.arm64.ARM64_OP_IMM and op.imm in flag_values:
                    print(f"0x{ins.address:08x}:  {ins.mnemonic:<8} {ins.op_str}")

if __name__ == "__main__":
    search_constants()
