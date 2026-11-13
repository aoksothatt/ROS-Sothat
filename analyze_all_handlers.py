import capstone, struct

with open(r'extracted\Payload\client.app\client', 'rb') as f:
    client_data = f.read()

# Load jump table
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

# For each handler, let's extract:
# 1. Does it read [sp, #0x60] (consts)?
# 2. Does it read [sp, #0x88] (names)?
# 3. Does it access [x22, #0x178] or [..., #0x178] (fastlocals)?
# 4. Does it access [x22, #0x30] (globals) or [x22, #0x38] (locals) or [x22, #0x28] (builtins)?
# 5. BL targets (calls)
# 6. First 5 instructions

results = []
for op, va in sorted(handlers.items()):
    off = va - 0x100000000
    code = client_data[off:off+120]
    insns = []
    bls = []
    features = set()
    for ins in md.disasm(code, va):
        insns.append(f"{ins.mnemonic} {ins.op_str}")
        if ins.mnemonic == 'bl':
            bls.append(ins.op_str)
        if '#0x60' in ins.op_str:
            features.add('CONSTS')
        if '#0x88' in ins.op_str:
            features.add('NAMES')
        if '#0x178' in ins.op_str:
            features.add('FASTLOCALS')
        if '#0x30' in ins.op_str:
            features.add('GLOBALS')
        if '#0x38' in ins.op_str:
            features.add('LOCALS')
        if ins.mnemonic in ('b', 'br') and ins.address > va + 16:
            break
    results.append({
        'op': op,
        'va': hex(va),
        'features': list(features),
        'bls': bls[:3],
        'preview': insns[:4]
    })

print(f"Total analyzed: {len(results)}")
for r in results[:25]:
    print(f"Op {r['op']:3d} ({hex(r['op'])}) -> VA {r['va']} feat={r['features']} bls={r['bls']}")
    for p in r['preview']:
        print(f"     {p}")
