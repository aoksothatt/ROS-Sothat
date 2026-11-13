from full_unmarshaler import load_script
from inspect_channel_login import inspect_code

print("=== entities/iRosMatchAvatar.py ===")
co_rma = load_script(r'extracted\scripts\entities\iRosMatchAvatar.py.raw')
inspect_code(co_rma)

print("\n=== entities/iRosMatch.py ===")
co_rm = load_script(r'extracted\scripts\entities\iRosMatch.py.raw')
inspect_code(co_rm)
