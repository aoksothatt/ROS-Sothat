import zipfile, capstone

with zipfile.ZipFile('RoS-Legacy-iOS.ipa') as z:
    client_data = z.read('Payload/client.app/client')

md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)

for name, off in [("Function at 0x101096a38", 0x1096a38), ("Function at 0x101096b28", 0x1096b28)]:
    code = client_data[off:off+250]
    print(f"\n=== {name} ===")
    for ins in md.disasm(code, 0x100000000 + off):
        print(f"  0x{ins.address:x}: {ins.mnemonic} {ins.op_str}")
        if ins.mnemonic == 'ret':
            break
