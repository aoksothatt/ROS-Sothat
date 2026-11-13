import os
from full_unmarshaler import load_script

hits = []
for root, dirs, files in os.walk(r'extracted\scripts'):
    for f in files:
        if f.endswith('.raw'):
            path = os.path.join(root, f)
            try:
                co = load_script(path)
                # Check names
                def search_co(c):
                    names = [n[1].decode('latin1', errors='ignore') if isinstance(n[1], bytes) else str(n[1]) for n in c['names'][1]]
                    if 'connect' in names or 'login' in names:
                        rel = os.path.relpath(path, r'extracted\scripts')
                        hits.append((rel, names))
                    for sub in c['consts'][1]:
                        if sub[0] == 'code':
                            search_co(sub[1])
                search_co(co)
            except Exception:
                pass

print(f"Total matching files: {len(hits)}")
for rel, names in hits[:25]:
    matched = [n for n in names if 'connect' in n.lower() or 'login' in n.lower()]
    print(f"{rel}: {matched}")
