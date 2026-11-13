from full_unmarshaler import load_script

code = load_script(r'extracted\scripts\ui\UILogin.py.raw')
names = [n[1].decode('latin1', errors='ignore') if isinstance(n[1], bytes) else str(n[1]) for n in code['names'][1]]
const_strs = []
for c in code['consts'][1]:
    if c[0] in ('string', 'unicode'):
        s = c[1].decode('latin1', errors='ignore') if isinstance(c[1], bytes) else str(c[1])
        const_strs.append(s)

print("UILogin top-level names:")
print(names)
print("\nUILogin top-level const strings:")
print(const_strs[:30])
