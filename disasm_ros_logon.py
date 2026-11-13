from full_unmarshaler import load_script
from inspect_uilogin_methods import find_code

code = load_script(r'extracted\scripts\ui\UILogin.py.raw')
ros_logon = find_code(code, '_ros_logon')
if ros_logon:
    print("=== _ros_logon Code Object ===")
    print("Argcount:", ros_logon['argcount'])
    print("Varnames:", [v[1].decode('latin1', errors='ignore') if isinstance(v[1], bytes) else str(v[1]) for v in ros_logon['varnames'][1]])
    print("Names:", [n[1].decode('latin1', errors='ignore') if isinstance(n[1], bytes) else str(n[1]) for n in ros_logon['names'][1]])
    print("Consts:", [sc[1] for sc in ros_logon['consts'][1]])
    print("Raw code bytes:", [b for b in ros_logon['code'][1]])
