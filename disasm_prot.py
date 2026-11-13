import zipfile, capstone

with zipfile.ZipFile('RoS-Legacy-iOS.ipa') as z:
    client_data = z.read('Payload/client.app/client')

md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)

funcs = [
    ("Method #01 (0x1010965a8)", 0x10965a8, 120),
    ("Method #09 (0x1010969b0)", 0x10969b0, 250),
    ("Method #03 (0x101096f74)", 0x1096f74, 80),
]

for name, off, size in funcs:
    code = client_data[off:off+size]
    print(f"\n=== {name} ===")
    for ins in md.disasm(code, 0x100000000 + off):
        print(f"  0x{ins.address:x}: {ins.mnemonic} {ins.op_str}")
        if ins.mnemonic == 'ret':
            break
