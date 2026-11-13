import zipfile, capstone

with zipfile.ZipFile('RoS-Legacy-iOS.ipa') as z:
    client_data = z.read('Payload/client.app/client')

md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)

start_off = 0x1da6468
code = client_data[start_off:start_off + 350]
print(f"=== Decryption function at 0x101da6468 ===")
for ins in md.disasm(code, 0x100000000 + start_off):
    print(f"  0x{ins.address:x}: {ins.mnemonic} {ins.op_str}")
    if ins.mnemonic == 'ret':
        break
