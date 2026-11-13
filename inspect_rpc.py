from parse_redirect import NeoXUnmarshaler
from dump_subcodes import dump_code

with open(r'extracted\scripts\engine\common\rpc.py.raw', 'rb') as f:
    data = f.read()

u = NeoXUnmarshaler(data)
obj = u.read_object()
print('=== rpc.py ===')
dump_code(obj[1])
