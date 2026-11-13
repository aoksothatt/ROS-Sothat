import struct

def deobfuscate_string(data):
    b = bytearray(data)
    L = len(b)
    for i in range(L):
        b[i] ^= ((L - 1 - i) & 0xff)
    return bytes(b)

# Test on redirect.py
enc = b'xllnt`gw,qy'
dec = deobfuscate_string(enc)
print('Test decode:', enc, '->', dec)

# Test on <module>
enc_mod = b';jdiaf`>'
dec_mod = deobfuscate_string(enc_mod)
print('Test decode module:', enc_mod, '->', dec_mod)
