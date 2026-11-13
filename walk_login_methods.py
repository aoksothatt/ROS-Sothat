from full_unmarshaler import load_script

code = load_script(r'extracted\scripts\ui\UILogin.py.raw')

def walk(c):
    name = c['name'][1]
    if isinstance(name, bytes): name = name.decode('latin1', errors='ignore')
    if 'connect' in name.lower() or 'login' in name.lower():
        print("Match code:", name)
    for sub in c['consts'][1]:
        if sub[0] == 'code':
            walk(sub[1])

walk(code)
