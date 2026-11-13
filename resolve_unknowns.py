import os, glob
from test_full_unmarshal import FullNeoXUnmarshaler

out_dir = r'extracted\scripts'
raw_files = glob.glob(os.path.join(out_dir, 'unknown_*.raw'))
print(f'Found {len(raw_files)} unknown files to resolve...')

resolved = 0
failed = 0
for raw_path in raw_files:
    try:
        with open(raw_path, 'rb') as f:
            data = f.read()
        u = FullNeoXUnmarshaler(data)
        obj = u.read_object()
        if obj[0] == 'code':
            raw_fn = obj[1]['filename'][1]
            if isinstance(raw_fn, bytes):
                raw_fn = raw_fn.decode('utf-8', errors='ignore')
            fn_name = raw_fn.replace('\\', '/').lstrip('/')
            if ':' in fn_name:
                fn_name = fn_name.split(':', 1)[1].lstrip('/')
            
            dest_path = os.path.join(out_dir, fn_name) + '.raw'
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            with open(dest_path, 'wb') as out_f:
                out_f.write(data)
            os.remove(raw_path)
            resolved += 1
    except Exception as e:
        failed += 1
        print(f'Still failed: {os.path.basename(raw_path)}: {e}')

print(f'Resolution complete: Resolved {resolved}, Remaining failed: {failed}')
