import xdis.load

v, ts, mi, co, ip, ss, sh = xdis.load.load_module('redirect.pyc')
print("=== <module> co_code ===")
print([b for b in co.co_code])

for c in co.co_consts:
    if hasattr(c, 'co_code'):
        print(f"\n=== {c.co_name} ===")
        print("consts:", c.co_consts)
        print("names:", c.co_names)
        print("varnames:", c.co_varnames)
        print("code bytes:", [b for b in c.co_code])
