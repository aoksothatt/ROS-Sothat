from full_unmarshaler import load_script

code = load_script(r'extracted\scripts\entities\Account.py.raw')
print('=== Account.py ===')
print('Module names count:', len(code['names'][1]))

for c in code['consts'][1]:
    if c[0] == 'code':
        cls_code = c[1]
        cls_name = cls_code['name'][1].decode(errors='ignore') if isinstance(cls_code['name'][1], bytes) else cls_code['name'][1]
        print(f'\nClass: {cls_name}')
        methods = []
        for sub in cls_code['consts'][1]:
            if sub[0] == 'code':
                m_name = sub[1]['name'][1].decode(errors='ignore') if isinstance(sub[1]['name'][1], bytes) else sub[1]['name'][1]
                m_args = [v[1].decode(errors='ignore') if isinstance(v[1], bytes) else v[1] for v in sub[1]['varnames'][1][:sub[1]['argcount']]]
                methods.append(f"{m_name}({', '.join(m_args)})")
        print(f'Methods ({len(methods)}):')
        for m in methods:
            print(f'  - {m}')
