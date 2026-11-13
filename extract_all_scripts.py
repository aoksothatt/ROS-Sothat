import os, sys, struct, zlib
import rotor
from parse_redirect import NeoXUnmarshaler
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

ROTOR_KEY = b"zxp+3uexi,fjepkfap3341s~mnv+1we!/zxp+3uexi,fj$~ap3341sfjepkfap3341s+3uexifjepkfap3341exi,+3uex22i,+3t56uexi,+3ue34xi,+3u34exi,+tttuexi,+lzuexi,~mnv+1we!/zxp~mnv+1we!/zxp*&sfjepkfap3341sfjepkf1!,fjepkfap3341s~mnv+1we!/epkfap3341s~mnv+1we!/zxp+3uexi,fjepkfap3341s~mnv+1we!/zxp+3uexi,fjepkfap3341s~mnv+1we!/zxp!#+3u'"
AES_KEY = b'!@e}a6^C0dw5q4SW'

def _reverse_string(s):
    l = bytearray(s)
    for i in range(min(128, len(l))):
        l[i] ^= 154
    l.reverse()
    return bytes(l)

def decrypt_nxs(raw_data):
    rot = rotor.newrotor(ROTOR_KEY.decode('latin1'))
    dec = rot.decrypt(raw_data)
    decomp = zlib.decompress(dec)
    rev = _reverse_string(decomp)
    return rev

def decrypt_aes(raw_data):
    cipher_data = raw_data[4:]
    n_blocks = len(cipher_data) // 16
    cipher = Cipher(algorithms.AES(AES_KEY), modes.ECB())
    decryptor = cipher.decryptor()
    return decryptor.update(cipher_data[:n_blocks*16])

def main():
    npk_path = r'extracted\Payload\client.app\script.npk'
    out_dir = r'extracted\scripts'
    os.makedirs(out_dir, exist_ok=True)

    with open(npk_path, 'rb') as f:
        f.seek(51671674)
        entries = []
        for i in range(3983):
            entry = f.read(28)
            id_val, off, zsize, size, zcrc, crc = struct.unpack('<IIIIII', entry[:24])
            entries.append((id_val, off, zsize, size, i))

    print(f'Starting extraction of {len(entries)} files from script.npk...')
    
    file_manifest = []
    success_count = 0
    fail_count = 0

    with open(npk_path, 'rb') as f:
        for id_val, off, zsize, size, idx in entries:
            f.seek(off)
            raw = f.read(size)
            
            data = None
            fn_name = None
            is_redirect = (id_val == 0xfb54f059)
            
            try:
                if is_redirect:
                    data = decrypt_aes(raw)
                    fn_name = 'redirect.py'
                else:
                    data = decrypt_nxs(raw)
                
                # Unmarshal to get true filename
                u = NeoXUnmarshaler(data)
                obj = u.read_object()
                if obj[0] == 'code':
                    raw_fn = obj[1]['filename'][1]
                    if isinstance(raw_fn, bytes):
                        raw_fn = raw_fn.decode('utf-8', errors='ignore')
                    fn_name = raw_fn.replace('\\', '/')
                
                success_count += 1
            except Exception as e:
                fail_count += 1
                fn_name = f'unknown_{idx:04d}_0x{id_val:08x}.bin'
            
            if not fn_name:
                fn_name = f'unnamed_{idx:04d}_0x{id_val:08x}.bin'
            
            # Normalize path
            # Remove leading slashes or drive letters
            clean_fn = fn_name.lstrip('/\\')
            if ':' in clean_fn:
                clean_fn = clean_fn.split(':', 1)[1].lstrip('/\\')
            
            dest_path = os.path.join(out_dir, clean_fn)
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            
            if data:
                with open(dest_path + '.raw', 'wb') as out_f:
                    out_f.write(data)
            
            file_manifest.append({
                'index': idx,
                'id': f'0x{id_val:08x}',
                'path': clean_fn,
                'size': size,
                'status': 'ok' if data else 'failed'
            })
            
            if (idx + 1) % 500 == 0 or idx == len(entries) - 1:
                print(f'Processed {idx+1}/{len(entries)} files (Success: {success_count}, Failed: {fail_count})')

    print(f'Extraction complete! Total Success: {success_count}, Failed: {fail_count}')
    
    # Save manifest
    import json
    with open('extracted_manifest.json', 'w') as mf:
        json.dump(file_manifest, mf, indent=2)
    print('Manifest saved to extracted_manifest.json')

if __name__ == '__main__':
    main()
