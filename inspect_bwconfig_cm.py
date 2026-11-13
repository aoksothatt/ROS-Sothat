from full_unmarshaler import load_script
from inspect_channel_login import inspect_code

print("=== common/bwconfig.py ===")
co_bw = load_script(r'extracted\scripts\common\bwconfig.py.raw')
inspect_code(co_bw)

print("\n=== helpers/ConnectMonitor.py ===")
co_cm = load_script(r'extracted\scripts\helpers\ConnectMonitor.py.raw')
inspect_code(co_cm)
