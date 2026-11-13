import capstone

with open(r'extracted\Payload\client.app\client', 'rb') as f:
    f.seek(0x1cd8d2c)
    code = f.read(40)

md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
for ins in md.disasm(code, 0x101cd8d2c):
    print(f"0x{ins.address:x}: {ins.mnemonic:<10} {ins.op_str:<25}")
