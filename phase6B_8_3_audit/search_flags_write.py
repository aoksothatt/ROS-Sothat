import capstone

BINARY_PATH = "extracted/Payload/client.app/client"

def search_strh_60():
    with open(BINARY_PATH, "rb") as f:
        start_va = 0x100910000
        end_va = 0x100935000
        f.seek(start_va - 0x100000000)
        code = f.read(end_va - start_va)
        
    md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
    md.detail = True
    
    print("Searching for strh ..., [x..., #0x60] in Mercury code...")
    for ins in md.disasm(code, start_va):
        if ins.mnemonic == 'strh':
            # Check if second operand is memory with disp == 0x60
            if len(ins.operands) >= 2 and ins.operands[1].type == capstone.arm64.ARM64_OP_MEM:
                mem = ins.operands[1].mem
                if mem.disp == 0x60:
                    print(f"0x{ins.address:08x}:  {ins.mnemonic:<8} {ins.op_str}")

if __name__ == "__main__":
    search_strh_60()
