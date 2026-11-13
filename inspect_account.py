from resolve_last3 import CleanUnmarshaler

with open(r'extracted\scripts\entities\Account.py.raw', 'rb') as f:
    u = CleanUnmarshaler(f.read())
    code = u.read_object()[1]

def dump_cls(c, indent=0):
    pref = ' ' * indent
    name = c['name'][1].decode() if isinstance(c['name'][1], bytes) else str(c['name'][1])
    print(f'{pref}=== Class: {name} ===')
    methods = []
    subclasses = []
    for sub in c['consts'][1]:
        if sub[0] == 'code':
            sub_code = sub[1]
            sub_name = sub_code['name'][1].decode() if isinstance(sub_code['name'][1], bytes) else str(sub_code['name'][1])
            methods.append(sub_name)
    print(f'{pref}Methods ({len(methods)}):')
    for m in methods:
        print(f'{pref}  - {m}')

for c in code['consts'][1]:
    if c[0] == 'code':
        dump_cls(c[1])
