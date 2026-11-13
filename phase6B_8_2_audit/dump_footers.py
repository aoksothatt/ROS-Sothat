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

print("=== Piggybacks (0x1009229fc) ===")
dump_range(0x1009229fc, 25)

print("\n=== Indexed Channel (0x100922dc0) ===")
dump_range(0x100922dc0, 30)

print("\n=== ACKs (0x100922e4c) ===")
dump_range(0x100922e4c, 30)

print("\n=== Sequence Number (0x100922f50) ===")
dump_range(0x100922f50, 30)

print("\n=== Request Offset / Next (0x100922f70) ===")
dump_range(0x100922f70, 30)
