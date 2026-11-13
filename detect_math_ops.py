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
    off = struct.unpack('<H', raw[i*2:(i+1)*2])[0]
    va = base + (off << 2)
    if va != default_target:
        handlers[op] = va

md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)

slot_names = {
    0x00: 'BINARY_ADD',
    0x08: 'BINARY_SUBTRACT',
    0x10: 'BINARY_MULTIPLY',
    0x18: 'BINARY_DIVIDE',
    0x20: 'BINARY_MODULO',
    0x30: 'BINARY_POWER',
    0x38: 'UNARY_NEGATIVE',
    0x40: 'UNARY_POSITIVE',
    0x58: 'UNARY_INVERT',
    0x60: 'BINARY_LSHIFT',
    0x68: 'BINARY_RSHIFT',
    0x70: 'BINARY_AND',
    0x78: 'BINARY_XOR',
    0x80: 'BINARY_OR',
    0xb8: 'INPLACE_ADD',
    0xc0: 'INPLACE_SUBTRACT',
    0xc8: 'INPLACE_MULTIPLY',
    0xd0: 'INPLACE_DIVIDE',
    0xd8: 'INPLACE_MODULO',
    0xe0: 'INPLACE_POWER',
    0xe8: 'INPLACE_LSHIFT',
    0xf0: 'INPLACE_RSHIFT',
    0xf8: 'INPLACE_AND',
    0x100: 'INPLACE_XOR',
    0x108: 'INPLACE_OR',
    0x110: 'BINARY_FLOOR_DIVIDE',
    0x118: 'BINARY_TRUE_DIVIDE',
    0x120: 'INPLACE_FLOOR_DIVIDE',
    0x128: 'INPLACE_TRUE_DIVIDE'
}

detected = {}
for op, va in sorted(handlers.items()):
    off = va - 0x100000000
    code = client_data[off:off+80]
    for ins in md.disasm(code, va):
        # Look for bl to 0x101c32... or 0x101c33...
        if ins.mnemonic == 'bl' and ins.op_str.startswith('#0x101c3'):
            target_va = int(ins.op_str[3:], 16)
            # Disassemble first 6 instructions of target_va to find mov w2, #imm
            t_off = target_va - 0x100000000
            t_code = client_data[t_off:t_off+30]
            for t_ins in md.disasm(t_code, target_va):
                if t_ins.mnemonic == 'mov' and t_ins.op_str.startswith('w2, '):
                    imm_val = int(t_ins.op_str.split(', ')[1].lstrip('#'), 0)
                    if imm_val in slot_names:
                        detected[op] = slot_names[imm_val]
                        break

for op, name in sorted(detected.items()):
    print(f"Opcode {op:3d} (0x{op:02x}) -> {name}")
