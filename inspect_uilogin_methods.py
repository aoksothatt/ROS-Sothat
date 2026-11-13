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

uilogin = find_code(code, 'UILogin')
if uilogin:
    print("Found UILogin!")
    for c in uilogin['consts'][1]:
        if c[0] == 'code':
            m = c[1]
            m_name = m['name'][1].decode('latin1', errors='ignore') if isinstance(m['name'][1], bytes) else str(m['name'][1])
            varnames = [v[1].decode('latin1', errors='ignore') if isinstance(v[1], bytes) else str(v[1]) for v in m['varnames'][1]]
            names = [n[1].decode('latin1', errors='ignore') if isinstance(n[1], bytes) else str(n[1]) for n in m['names'][1]]
            print(f"Method: {m_name}")
            print(f"  Varnames: {varnames}")
            print(f"  Names: {names[:10]}")
