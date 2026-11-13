from full_unmarshaler import load_script

code = load_script(r'extracted\scripts\entities\Account.py.raw')
player_acc = [c[1] for c in code['consts'][1] if c[0] == 'code' and 'PlayerAccount' in str(c[1]['name'])][0]

for sub in player_acc['consts'][1]:
    if sub[0] == 'code':
        m = sub[1]
        m_name = m['name'][1].decode() if isinstance(m['name'][1], bytes) else m['name'][1]
        if m_name in ('onLogin', 'onChannelLogin', 'doActivation'):
            print(f'\n=== Method: {m_name} ===')
            print('  Varnames:', [v[1].decode() if isinstance(v[1], bytes) else v[1] for v in m['varnames'][1]])
            print('  Names:', [n[1].decode() if isinstance(n[1], bytes) else n[1] for n in m['names'][1]])
            print('  Consts:', [c[1] for c in m['consts'][1] if c[0] != 'code'])
