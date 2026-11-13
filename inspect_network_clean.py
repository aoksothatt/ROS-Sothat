from full_unmarshaler import load_script

co = load_script(r'extracted\scripts\engine\network.py.raw')
print("=== engine/network.py ===")
print("Names:", [n[1].decode('latin1', errors='ignore') if isinstance(n[1], bytes) else str(n[1]) for n in co['names'][1]])
for sc in co['consts'][1]:
    if sc[0] == 'code':
        m = sc[1]
        m_name = m['name'][1].decode('latin1', errors='ignore') if isinstance(m['name'][1], bytes) else str(m['name'][1])
        print(f"Func/Class: {m_name}")
        print("  Names:", [n[1].decode('latin1', errors='ignore') if isinstance(n[1], bytes) else str(n[1]) for n in m['names'][1]])
        print("  Varnames:", [v[1].decode('latin1', errors='ignore') if isinstance(v[1], bytes) else str(v[1]) for v in m['varnames'][1]])
