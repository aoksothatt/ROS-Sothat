import xdis.unmarshal
import xdis.std as dis

with open('redirect.pyc', 'rb') as f:
    f.seek(8)
    co = xdis.unmarshal.load_code(f, (2, 7))

print("co_name:", co.co_name)
print("co_argcount:", co.co_argcount)
print("co_varnames:", co.co_varnames)
print("co_cellvars:", co.co_cellvars)
print("co_freevars:", co.co_freevars)
print("\n--- Disassembly ---")
dis.disassemble(co)

for c in co.co_consts:
    if hasattr(c, 'co_code'):
        print(f"\n=== Sub-code {c.co_name} ===")
        print("  varnames:", c.co_varnames)
        print("  cellvars:", c.co_cellvars)
        print("  freevars:", c.co_freevars)
        try:
            dis.disassemble(c)
        except Exception as e:
            print("  Disasm failed:", e)
