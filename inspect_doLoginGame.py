from full_unmarshaler import load_script
from inspect_uilogin_methods import find_code

code = load_script(r'extracted\scripts\ui\UILogin.py.raw')
doLogin = find_code(code, 'doLoginGame')
if doLogin:
    print("Found doLoginGame!")
    print("Varnames:", [v[1].decode('latin1', errors='ignore') if isinstance(v[1], bytes) else str(v[1]) for v in doLogin['varnames'][1]])
    print("Names:", [n[1].decode('latin1', errors='ignore') if isinstance(n[1], bytes) else str(n[1]) for n in doLogin['names'][1]])
    consts = []
    for c in doLogin['consts'][1]:
        if c[0] != 'code':
            val = c[1].decode('latin1', errors='ignore') if isinstance(c[1], bytes) else str(c[1])
            consts.append(val)
    print("Consts:", consts[:30])
