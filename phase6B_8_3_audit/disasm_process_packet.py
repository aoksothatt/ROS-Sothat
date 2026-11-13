import capstone

BINARY_PATH = "extracted/Payload/client.app/client"

def dump_disasm(start_va, end_va):
    with open(BINARY_PATH, "rb") as f:
        file_off = start_va - 0x100000000
        f.seek(file_off)
        raw = f.read(end_va - start_va)
    
    md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
    lines = []
    for ins in md.disasm(raw, start_va):
        lines.append(f"0x{ins.address:08x}:  {ins.mnemonic:<8} {ins.op_str}")
    return lines

if __name__ == "__main__":
    # Let's inspect 0x100923300 - 0x100924000
    lines = dump_disasm(0x100923300, 0x100923600)
    for l in lines[:60]:
        print(l)
