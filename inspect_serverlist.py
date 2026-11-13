from full_unmarshaler import load_script
from inspect_channel_login import inspect_code

code = load_script(r'extracted\scripts\common\serverlist_utils.py.raw')
inspect_code(code)
