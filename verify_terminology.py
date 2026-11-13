import os, re
from full_unmarshaler import load_script

# 1. Search binary for LoginApp, BaseApp, CellApp, BigWorld, NeoX
print("=== 1. Mach-O Binary Search ===")
with open(r'extracted\Payload\client.app\client', 'rb') as fp:
    macho_data = fp.read()

terms = [
    b'NeoX', b'neox', b'game3d', b'NXPK',
    b'BigWorld', b'bwconfig', b'logOn',
    b'loginapp', b'baseapp', b'cellapp',
    b'LoginApp', b'BaseApp', b'CellApp',
    b'login_app', b'base_app', b'cell_app',
    b'PyEval_EvalFrameEx', b'Boost.Python', b'boost::python'
]

for t in terms:
    matches = []
    start = 0
    while len(matches) < 5:
        idx = macho_data.find(t, start)
        if idx == -1: break
        matches.append(idx)
        start = idx + len(t)
    print(f"Binary string '{t.decode('latin1')}': count={len(matches)}+, sample offsets={[hex(m) for m in matches[:3]]}")

# 2. Search scripts for loginapp, baseapp, cellapp, BigWorld, base, cell
print("\n=== 2. Script Search for Terminology ===")
term_hits = {
    'loginapp': [], 'baseapp': [], 'cellapp': [],
    'LoginApp': [], 'BaseApp': [], 'CellApp': [],
    'BigWorld': [], 'bwconfig': [], 'self.base': [], 'self.cell': []
}

for root, dirs, files in os.walk(r'extracted\scripts'):
    for f in files:
        if f.endswith('.raw'):
            path = os.path.join(root, f)
            rel = os.path.relpath(path, r'extracted\scripts')
            try:
                co = load_script(path)
                
                # collect all names and string consts
                names = []
                strs = []
                def extract_terms(c):
                    for n in c['names'][1]:
                        val = n[1].decode('latin1', errors='ignore') if isinstance(n[1], bytes) else str(n[1])
                        names.append(val)
                    for sc in c['consts'][1]:
                        if sc[0] in ('string', 'unicode'):
                            val = sc[1].decode('latin1', errors='ignore') if isinstance(sc[1], bytes) else str(sc[1])
                            strs.append(val)
                        elif sc[0] == 'code':
                            extract_terms(sc[1])
                extract_terms(co)
                
                all_text = " ".join(names + strs)
                for k in ['loginapp', 'baseapp', 'cellapp', 'LoginApp', 'BaseApp', 'CellApp', 'BigWorld', 'bwconfig']:
                    if k in all_text:
                        term_hits[k].append(rel)
                if 'base' in names:
                    term_hits['self.base'].append(rel)
                if 'cell' in names:
                    term_hits['self.cell'].append(rel)
            except Exception:
                pass

for k, v in term_hits.items():
    print(f"Script occurrences of '{k}': in {len(v)} files (sample: {v[:3]})")
