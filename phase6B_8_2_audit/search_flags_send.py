import capstone

BINARY_PATH = "extracted/Payload/client.app/client"

def search_flags_in_range(start_va, count):
    with open(BINARY_PATH, "rb") as f:
        f.seek(start_va - 0x100000000)
        raw = f.read(count * 4)
    md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
    for ins in md.disasm(raw, start_va):
        if ins.mnemonic in ['tbnz', 'tbz']:
            print(f"0x{ins.address:08x}:  {ins.mnemonic:<8} {ins.op_str}")

# Let's inspect Nub::send around 0x100921dc0 or where 0x1030a2c26 was found
print("=== Search near 0x100921d00 ===")
search_flags_in_range(0x100921c00, 150)
