import capstone, struct

with open(r'extracted\Payload\client.app\client', 'rb') as f:
    client_data = f.read()

# Load jump table
f_off = 0x2bebbac
raw = client_data[f_off:f_off + 201*2]
base = 0x101cd8d84
handlers = {}
for i in range(201):
    op = i + 3
    off = struct.unpack('<H', raw[i*2:(i+1)*2])[0]
    handlers[op] = base + (off << 2)

md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)

for op in [101, 153, 155, 157, 134, 131, 93, 104, 96, 57, 74]:
    va = handlers.get(op, 0)
    print(f"\n=== Opcode {op} (0x{op:02x}) -> VA 0x{va:x} ===")
    off = va - 0x100000000
    code = client_data[off:off+60]
    for ins in md.disasm(code, va):
        print(f"  0x{ins.address:x}: {ins.mnemonic:<10} {ins.op_str}")
        if ins.mnemonic in ('b', 'br') and ins.address > va:
            break
