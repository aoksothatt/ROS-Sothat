import capstone

with open(r'extracted\Payload\client.app\client', 'rb') as f:
    client_data = f.read()

import struct
f_off = 0x2bebbac
raw = client_data[f_off:f_off + 201*2]
base = 0x101cd8d84
md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)

for op in [135, 136, 132, 82, 54, 67, 27, 25]:
    off = struct.unpack('<H', raw[(op-3)*2:(op-2)*2])[0]
    va = base + (off << 2)
    print(f"\n=== Opcode {op} -> VA 0x{va:x} ===")
    code = client_data[va - 0x100000000 : va - 0x100000000 + 40]
    for ins in md.disasm(code, va):
        print(f"  {ins.mnemonic:<8} {ins.op_str}")
