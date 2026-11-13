from full_unmarshaler import load_script

code = load_script(r'extracted\scripts\ui\UILogin.py.raw')

def find_code(c, target):
    name = c['name'][1]
    if isinstance(name, bytes): name = name.decode('latin1', errors='ignore')
    if name == target: return c
    for sub in c['consts'][1]:
        if sub[0] == 'code':
            res = find_code(sub[1], target)
            if res: return res
    return None

m = find_code(code, 'connectLoginHost')
if m:
    print("=== Found connectLoginHost ===")
    print("Varnames:", [v[1].decode('latin1', errors='ignore') if isinstance(v[1], bytes) else str(v[1]) for v in m['varnames'][1]])
    print("Names:", [n[1].decode('latin1', errors='ignore') if isinstance(n[1], bytes) else str(n[1]) for n in m['names'][1]])
    print("Consts:", [str(sc[1]) for sc in m['consts'][1] if sc[0] != 'code'][:25])
    subcodes = [sc[1] for sc in m['consts'][1] if sc[0] == 'code']
    for sc in subcodes:
        s_name = sc['name'][1].decode('latin1', errors='ignore') if isinstance(sc['name'][1], bytes) else str(sc['name'][1])
        print("  Subcode:", s_name)
        print("    Varnames:", [v[1].decode('latin1', errors='ignore') if isinstance(v[1], bytes) else str(v[1]) for v in sc['varnames'][1]])
        print("    Names:", [n[1].decode('latin1', errors='ignore') if isinstance(n[1], bytes) else str(n[1]) for n in sc['names'][1]])
        print("    Consts:", [str(c[1]) for c in sc['consts'][1] if c[0] != 'code'][:25])
