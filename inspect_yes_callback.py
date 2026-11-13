from full_unmarshaler import load_script
from inspect_uilogin_methods import find_code

code = load_script(r'extracted\scripts\ui\UILogin.py.raw')
doLogin = find_code(code, 'doLoginGame')
if doLogin:
    for c in doLogin['consts'][1]:
        if c[0] == 'code':
            m = c[1]
            m_name = m['name'][1].decode('latin1', errors='ignore') if isinstance(m['name'][1], bytes) else str(m['name'][1])
            print("Sub-method:", m_name)
            print("  Varnames:", [v[1].decode('latin1', errors='ignore') if isinstance(v[1], bytes) else str(v[1]) for v in m['varnames'][1]])
            print("  Names:", [n[1].decode('latin1', errors='ignore') if isinstance(n[1], bytes) else str(n[1]) for n in m['names'][1]])
            print("  Consts:", [str(sc[1]) for sc in m['consts'][1] if sc[0] != 'code'][:15])
