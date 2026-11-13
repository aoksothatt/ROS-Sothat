import capstone

with open('extracted/Payload/client.app/client', 'rb') as f:
    data = f.read()

md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)

for va, name in [(0x10093e95c, "fn_10093e95c"), (0x10093e078, "fn_10093e078")]:
    print(f"=== Disassembly of {name} at 0x{va:x} ===")
    start_off = va - 0x100000000
    code = data[start_off:start_off + 0x60]
    for i in md.disasm(code, va):
        print(f"  0x{i.address:x}: {i.mnemonic} {i.op_str}")
