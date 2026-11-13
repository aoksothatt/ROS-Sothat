from full_unmarshaler import load_script
from inspect_channel_login import inspect_code

co = load_script(r'extracted\scripts\engine\common\rpc.py.raw')
for sc in co['consts'][1]:
    if sc[0] == 'code' and 'RPCObj' in str(sc[1]['name']):
        inspect_code(sc[1])
