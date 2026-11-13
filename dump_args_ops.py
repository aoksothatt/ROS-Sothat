import capstone, struct

with open(r'extracted\Payload\client.app\client', 'rb') as f:
    client_data = f.read()

f_off = 0x2bebbac
raw = client_data[f_off:f_off + 201*2]
base = 0x101cd8d84
default_target = 0x101cdd9e0

handlers = {}
for i in range(201):
    op = i + 3
    if op >= 90:
        off = struct.unpack('<H', raw[i*2:(i+1)*2])[0]
        va = base + (off << 2)
        if va != default_target:
            handlers[op] = va

md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)

for op, va in sorted(handlers.items()):
    off = va - 0x100000000
    code = client_data[off:off+60]
    lines = []
    for ins in md.disasm(code, va):
        lines.append(f"{ins.mnemonic:<8} {ins.op_str}")
        if len(lines) >= 8:
            break
    print(f"\n=== Opcode {op:3d} (0x{op:02x}) -> VA 0x{va:x} ===")
    for l in lines:
        print(f"  {l}")
