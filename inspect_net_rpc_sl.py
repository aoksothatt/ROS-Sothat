from full_unmarshaler import load_script
from inspect_channel_login import inspect_code

print("=== engine/network.py ===")
try:
    co_net = load_script(r'extracted\scripts\engine\network.py.raw')
    inspect_code(co_net)
except Exception as e:
    print("Error loading engine/network.py:", e)

print("\n=== engine/common/rpc.py ===")
try:
    co_rpc = load_script(r'extracted\scripts\engine\common\rpc.py.raw')
    inspect_code(co_rpc)
except Exception as e:
    print("Error loading engine/common/rpc.py:", e)

print("\n=== ui/UIServerList.py ===")
try:
    co_sl = load_script(r'extracted\scripts\ui\UIServerList.py.raw')
    inspect_code(co_sl)
except Exception as e:
    print("Error loading ui/UIServerList.py:", e)
