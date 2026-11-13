from full_unmarshaler import load_script
from inspect_uilogin_methods import find_code

code = load_script(r'extracted\scripts\ui\UILogin.py.raw')
m = find_code(code, 'startLogin')
if m:
    print("Found startLogin!")
    print("Varnames:", [v[1].decode('latin1', errors='ignore') if isinstance(v[1], bytes) else str(v[1]) for v in m['varnames'][1]])
    print("Names:", [n[1].decode('latin1', errors='ignore') if isinstance(n[1], bytes) else str(n[1]) for n in m['names'][1]])
    print("Consts:", [str(sc[1]) for sc in m['consts'][1] if sc[0] != 'code'][:25])
