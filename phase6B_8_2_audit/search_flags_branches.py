import capstone

BINARY_PATH = "extracted/Payload/client.app/client"

def search_branches():
    with open(BINARY_PATH, "rb") as f:
        f.seek(0x100922860 - 0x100000000)
        raw = f.read(0x100923500 - 0x100922860)
    
    md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
    for ins in md.disasm(raw, 0x100922860):
        if ins.mnemonic in ['tbnz', 'tbz']:
            print(f"0x{ins.address:08x}:  {ins.mnemonic:<8} {ins.op_str}")

search_branches()
