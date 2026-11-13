import os, json, hashlib
from full_unmarshaler import load_script, FullUnmarshaler

SCRIPTS_DIR = r'extracted\scripts'
MANIFEST_PATH = 'extracted_manifest.json'

# 1. Manifest audit
manifest_count = 0
manifest_entries = []
if os.path.exists(MANIFEST_PATH):
    with open(MANIFEST_PATH, 'r') as f:
        manifest_entries = json.load(f)
        manifest_count = len(manifest_entries)

print(f"Manifest entry count: {manifest_count}")

# 2. Disk scan of extracted/scripts
files_on_disk = []
for root, dirs, files in os.walk(SCRIPTS_DIR):
    for f in files:
        full_path = os.path.join(root, f)
        rel_path = os.path.relpath(full_path, SCRIPTS_DIR)
        files_on_disk.append((full_path, rel_path, os.path.getsize(full_path)))

total_files_on_disk = len(files_on_disk)
print(f"Total files on disk in {SCRIPTS_DIR}: {total_files_on_disk}")

# Check for empty files
empty_files = [r for full, r, size in files_on_disk if size == 0]
print(f"Empty files (size == 0): {len(empty_files)}")

# Check for duplicates by SHA256
hash_map = {}
duplicates = []
for full, r, size in files_on_disk:
    with open(full, 'rb') as fp:
        h = hashlib.sha256(fp.read()).hexdigest()
    if h in hash_map:
        duplicates.append((r, hash_map[h]))
    else:
        hash_map[h] = r

print(f"Unique SHA256 hashes: {len(hash_map)}")
print(f"Duplicate content instances: {len(duplicates)}")
if duplicates:
    print(f"Sample duplicates (up to 5): {duplicates[:5]}")

# 3. Test parsing each file with FullUnmarshaler
parsed_success = 0
parsed_failed = 0
fail_reasons = {}
recognizable_code_objects = 0
non_code_objects = 0

for full, r, size in files_on_disk:
    try:
        with open(full, 'rb') as fp:
            data = fp.read()
        u = FullUnmarshaler(data)
        obj_type, obj_val = u.read_object()
        parsed_success += 1
        if obj_type == 'code':
            recognizable_code_objects += 1
        else:
            non_code_objects += 1
    except Exception as e:
        parsed_failed += 1
        err = f"{type(e).__name__}: {str(e)[:60]}"
        fail_reasons[err] = fail_reasons.get(err, 0) + 1

print(f"\nParsing Summary:")
print(f"  Successfully parsed: {parsed_success}")
print(f"  Failed to parse: {parsed_failed}")
print(f"  Recognizable Python 'code' objects: {recognizable_code_objects}")
print(f"  Recognizable non-code objects: {non_code_objects}")
if fail_reasons:
    print(f"  Failure reasons: {fail_reasons}")
