import capstone

with open(r'extracted\Payload\client.app\client', 'rb') as f:
    client_data = f.read()

md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)

targets = [0x101c32aa0, 0x101c339cc, 0x101c32b40, 0x101c33b70, 0x101c33424, 0x101c33564, 0x101c7b230, 0x101c32a00, 0x101c33af8]

for t in targets:
    off = t - 0x100000000
    code = client_data[off:off+30]
    print(f"\nFunction at 0x{t:x}:")
    for ins in md.disasm(code, t):
        print(f"  0x{ins.address:x}: {ins.mnemonic:<10} {ins.op_str}")
