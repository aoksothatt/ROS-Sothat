from full_unmarshaler import load_script

code = load_script(r'extracted\scripts\helpers\channel\channel_login.py.raw')

def inspect_code(co, depth=0):
    indent = "  " * depth
    name = co['name'][1]
    if isinstance(name, bytes): name = name.decode('latin1', errors='ignore')
    fn = co['filename'][1]
    if isinstance(fn, bytes): fn = fn.decode('latin1', errors='ignore')
    print(f"{indent}=== Code: {name} ({fn}) ===")
    
    varnames = [v[1].decode('latin1', errors='ignore') if isinstance(v[1], bytes) else str(v[1]) for v in co['varnames'][1]]
    names = [n[1].decode('latin1', errors='ignore') if isinstance(n[1], bytes) else str(n[1]) for n in co['names'][1]]
    const_strs = []
    subcodes = []
    for c in co['consts'][1]:
        if c[0] == 'code':
            subcodes.append(c[1])
        elif c[0] in ('string', 'unicode') and len(c[1]) > 0:
            s = c[1].decode('latin1', errors='ignore') if isinstance(c[1], bytes) else str(c[1])
            const_strs.append(s)
        elif c[0] in ('int', 'int64', 'float'):
            const_strs.append(str(c[1]))
            
    if varnames:
        print(f"{indent}  Varnames ({len(varnames)}): {varnames[:15]}")
    if names:
        print(f"{indent}  Names ({len(names)}): {names[:20]}")
    if const_strs:
        print(f"{indent}  Consts ({len(const_strs)}): {const_strs[:15]}")
        
    for sub in subcodes:
        inspect_code(sub, depth + 1)

inspect_code(code)
