import zipfile, capstone

with zipfile.ZipFile('RoS-Legacy-iOS.ipa') as z:
    client_data = z.read('Payload/client.app/client')

md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)

methods = [
    ("Method_07 (0x101a720d4)", 0x1a720d4, 0x1a72208),
    ("Method_03 (0x101a72208)", 0x1a72208, 0x1a72bb0),
    ("Method_04 (0x101a72bb0)", 0x1a72bb0, 0x1a72cd8),
    ("Method_05 (0x101a72cd8)", 0x1a72cd8, 0x1a72e20),
    ("Method_08 (0x101a72e20)", 0x1a72e20, 0x1a72f50),
    ("Method_09 (0x101a72f50)", 0x1a72f50, 0x1a73190),
    ("Method_10 (0x101a73190)", 0x1a73190, 0x1a732d0),
]

for name, start_off, end_off in methods:
    code = client_data[start_off:min(start_off + 200, end_off)]
    print(f"\n=== {name} (first {len(code)} bytes) ===")
    for ins in md.disasm(code, 0x100000000 + start_off):
        print(f"  0x{ins.address:x}: {ins.mnemonic} {ins.op_str}")
        if ins.mnemonic == 'ret':
            break
