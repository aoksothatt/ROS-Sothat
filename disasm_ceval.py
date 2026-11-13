import capstone

with open(r'extracted\Payload\client.app\client', 'rb') as f:
    f.seek(0x1cdda1c - 100)
    code = f.read(250)

md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
for ins in md.disasm(code, 0x101cdda1c - 100):
    marker = "  <--- DEFAULT: unknown opcode" if ins.address == 0x101cdda1c else ""
    print(f"0x{ins.address:x}: {ins.mnemonic:<10} {ins.op_str:<25} {marker}")
