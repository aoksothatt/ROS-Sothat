import capstone

BINARY_PATH = "extracted/Payload/client.app/client"

def disasm_range(start_va, count=100, end_va=None):
    with open(BINARY_PATH, "rb") as f:
        file_off = start_va - 0x100000000
        f.seek(file_off)
        raw = f.read(count * 4 if end_va is None else (end_va - start_va))
    
    md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
    md.detail = True
    
    lines = []
    for ins in md.disasm(raw, start_va):
        lines.append(f"0x{ins.address:08x}:  {ins.mnemonic:<8} {ins.op_str}")
        if end_va and ins.address >= end_va:
            break
    return lines

if __name__ == "__main__":
    # Test on EncryptionFilter::send area
    res = disasm_range(0x10091c6cc, 80)
    for l in res[:30]:
        print(l)
