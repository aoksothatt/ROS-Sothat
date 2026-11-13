import capstone

BINARY_PATH = "extracted/Payload/client.app/client"

def dump_range(va, count):
    with open(BINARY_PATH, "rb") as f:
        file_off = va - 0x100000000
        f.seek(file_off)
        raw = f.read(count * 4)
    md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
    for ins in md.disasm(raw, va):
        print(f"0x{ins.address:08x}:  {ins.mnemonic:<8} {ins.op_str}")

print("=== Footer sizes (0x100918008 - 0x100918070) ===")
dump_range(0x100918008, 30)
