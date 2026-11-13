import zlib, struct
import rotor
from parse_redirect import NeoXUnmarshaler

ROTOR_KEY = b"zxp+3uexi,fjepkfap3341s~mnv+1we!/zxp+3uexi,fj$~ap3341sfjepkfap3341s+3uexifjepkfap3341exi,+3uex22i,+3t56uexi,+3ue34xi,+3u34exi,+tttuexi,+lzuexi,~mnv+1we!/zxp~mnv+1we!/zxp*&sfjepkfap3341sfjepkf1!,fjepkfap3341s~mnv+1we!/epkfap3341s~mnv+1we!/zxp+3uexi,fjepkfap3341s~mnv+1we!/zxp+3uexi,fjepkfap3341s~mnv+1we!/zxp!#+3u'"

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

# Read Entry 0 from script.npk
with open(r'extracted\Payload\client.app\script.npk', 'rb') as f:
    f.seek(51671674)
    entry = f.read(28)
    id_val, off, zsize, size, zcrc, crc = struct.unpack('<IIIIII', entry[:24])
    f.seek(off)
    raw = f.read(size)

print(f'Testing Entry #0 ID=0x{id_val:08x} off={off} size={size}...')
rev = decrypt_nxs(raw)
print('SUCCESSFULLY DECRYPTED & DECOMPRESSED! Plain length:', len(rev))
print('First 32 bytes hex:', rev[:32].hex())

u = NeoXUnmarshaler(rev)
obj = u.read_object()
print('SUCCESSFULLY UNMARSHALED SCRIPT!')
print('Filename:', obj[1]['filename'])
print('Code Name:', obj[1]['name'])
print('Consts count:', len(obj[1]['consts'][1]))
print('Names count:', len(obj[1]['names'][1]))
print('Names preview:', [n[1].decode(errors='ignore') if isinstance(n[1], bytes) else n[1] for n in obj[1]['names'][1][:15]])
