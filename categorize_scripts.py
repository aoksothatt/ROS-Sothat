import os, glob
from resolve_last3 import CleanUnmarshaler

out_dir = r'extracted\scripts'
all_raw_files = glob.glob(os.path.join(out_dir, '**', '*.raw'), recursive=True)
print(f'Total extracted raw script files: {len(all_raw_files)}')

interesting_files = []
network_files = []
entity_files = []

for p in all_raw_files:
    rel_p = os.path.relpath(p, out_dir).replace('\\', '/')
    rel_lower = rel_p.lower()
    if 'network' in rel_lower or 'packet' in rel_lower or 'socket' in rel_lower or 'protocol' in rel_lower or 'rpc' in rel_lower or 'gate' in rel_lower:
        network_files.append(rel_p)
    elif 'entities/' in rel_lower or 'player/' in rel_lower:
        entity_files.append(rel_p)

print(f'\nFound {len(network_files)} network/protocol/RPC related files:')
for nf in sorted(network_files)[:25]:
    print('  ', nf)

print(f'\nFound {len(entity_files)} entity/player files:')
for ef in sorted(entity_files)[:25]:
    print('  ', ef)
