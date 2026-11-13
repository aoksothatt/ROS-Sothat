from full_unmarshaler import load_script

code = load_script(r'extracted\scripts\ui\UILogin.py.raw')
print("UILogin names count:", len(code['names'][1]))

classes = []
methods = []

for c in code['consts'][1]:
    if c[0] == 'code':
        sub = c[1]
        s_name = sub['name'][1].decode('latin1', errors='ignore') if isinstance(sub['name'][1], bytes) else str(sub['name'][1])
        sub_methods = []
        for sc in sub['consts'][1]:
            if sc[0] == 'code':
                m_name = sc[1]['name'][1].decode('latin1', errors='ignore') if isinstance(sc[1]['name'][1], bytes) else str(sc[1]['name'][1])
                sub_methods.append(m_name)
        classes.append((s_name, sub_methods))

print("\nClasses in UILogin.py:")
for cls_name, m_list in classes:
    print(f"Class {cls_name} ({len(m_list)} methods):")
    for m in m_list[:15]:
        print(f"  - {m}")
