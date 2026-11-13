import struct, zlib
import rotor

def init_rotor():
    asdf_dn = 'j2h56ogodh3se'
    asdf_dt = '=dziaq.'
    asdf_df = '|os=5v7!"-234'
    asdf_tm = asdf_dn * 4 + (asdf_dt + asdf_dn + asdf_df) * 5 + \
        '!' + '#' + asdf_dt * 7 + asdf_df * 2 + '*' + '&' + "'"
    rot = rotor.newrotor(asdf_tm)
    return rot

def Clamp8(i):
    return i % (1 << 8)

def Clamp32(i):
    return i % (1 << 32)

def ROL32(n, d):
    return ((n << d) % (1 << 32)) | (n >> (32 - d))

def ROR32(n, d):
    return ROL32(n, 32-d)

def LShift8(n, d):
    return (n << d) % (1 << 8)

def RShift8(n, d):
    return n >> d

def BytesToInt32(b):
    return struct.unpack('<I', b)[0]

def Int32ToBytes(i):
    return struct.pack('<I', i)

def Decrypt(buffer, key=0x18B7A467):
    buffer = bytearray(buffer)
    size = len(buffer)
    dword = key
    for i in range(size//4):
        dword = ~(dword ^ ROR32(BytesToInt32(buffer[i*4:i*4+4]), 32-(i & 0x1F)))
        buffer[i*4:i*4+4] = Int32ToBytes(Clamp32(dword))
    base = size//4*4
    for i in range(size % 4):
        byte = buffer[base+i]
        byte = (RShift8(byte, 8-i) | LShift8(byte, i)) ^ RShift8(dword, i*8)
        buffer[base+i] = Clamp8(~byte)
    return bytes(buffer)

with open(r'extracted\Payload\client.app\script.npk', 'rb') as f:
    f.seek(51671674)
    entry = f.read(28)
    h, off, csize, usize, crc1, crc2, flg = struct.unpack('<7I', entry)
    f.seek(off)
    raw = f.read(csize)

print('Raw hex[:32]:', raw[:32].hex())

rot = init_rotor()
r_dec = rot.decrypt(raw)
print('Rotor(raw) hex[:32]:', r_dec[:32].hex())

buf_dec = Decrypt(raw)
print('Decrypt(raw) hex[:32]:', buf_dec[:32].hex())

rot2 = init_rotor()
r_buf_dec = rot2.decrypt(buf_dec)
print('Rotor(Decrypt(raw)) hex[:32]:', r_buf_dec[:32].hex())

try:
    z = zlib.decompress(r_buf_dec)
    print('SUCCESS on Rotor(Decrypt(raw))! Len:', len(z))
except Exception as e:
    print('Failed zlib on Rotor(Decrypt(raw)):', e)
