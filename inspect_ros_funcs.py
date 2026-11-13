from full_unmarshaler import load_script
from inspect_uilogin_methods import find_code

code = load_script(r'extracted\scripts\ui\UILogin.py.raw')

for name in ['_ros_doc_dirs', '_ros_cred', '_ros_logon', '_ros_logon_wrapped']:
    m = find_code(code, name)
    if m:
        print(f"\n=== Found {name} ===")
        print("Varnames:", [v[1].decode('latin1', errors='ignore') if isinstance(v[1], bytes) else str(v[1]) for v in m['varnames'][1]])
        print("Names:", [n[1].decode('latin1', errors='ignore') if isinstance(n[1], bytes) else str(n[1]) for n in m['names'][1]])
        consts = []
        for sc in m['consts'][1]:
            if sc[0] != 'code':
                consts.append(str(sc[1]))
        print("Consts:", consts[:20])
