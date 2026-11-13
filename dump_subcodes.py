from parse_redirect import u, obj

def dump_code(code_dict, indent=0):
    prefix = ' ' * indent
    name = code_dict['name'][1].decode() if isinstance(code_dict['name'][1], bytes) else str(code_dict['name'][1])
    fn = code_dict['filename'][1].decode() if isinstance(code_dict['filename'][1], bytes) else str(code_dict['filename'][1])
    print(f"{prefix}Code: {name} ({fn})")
    print(f"{prefix}  Varnames: {[v[1].decode() if isinstance(v[1], bytes) else v[1] for v in code_dict['varnames'][1]]}")
    print(f"{prefix}  Names: {[n[1].decode() if isinstance(n[1], bytes) else n[1] for n in code_dict['names'][1]]}")
    print(f"{prefix}  Consts:")
    for c in code_dict['consts'][1]:
        if c[0] == 'code':
            dump_code(c[1], indent + 4)
        else:
            val = c[1]
            if isinstance(val, bytes):
                val = repr(val)
            print(f"{prefix}    {c[0]}: {val}")

for c in obj[1]['consts'][1]:
    if c[0] == 'code':
        dump_code(c[1])
        print('-'*50)
