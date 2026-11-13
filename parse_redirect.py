import struct, sys

def deobfuscate_string(data):
    b = bytearray(data)
    L = len(b)
    for i in range(L):
        b[i] ^= ((L - 1 - i) & 0xff)
    return bytes(b)

class NeoXUnmarshaler:
    def __init__(self, data):
        self.data = data
        self.pos = 0
        self.interned = []

    def read_byte(self):
        b = self.data[self.pos]
        self.pos += 1
        return b

    def read_bytes(self, n):
        res = self.data[self.pos:self.pos+n]
        self.pos += n
        return res

    def read_long(self):
        val = struct.unpack('<i', self.read_bytes(4))[0]
        return val

    def read_object(self):
        type_code = chr(self.read_byte())
        if type_code == 'N':
            return ('None', None)
        elif type_code == 'T':
            return ('True', True)
        elif type_code == 'F':
            return ('False', False)
        elif type_code == 'i':
            val = self.read_long()
            return ('int', val)
        elif type_code == 'I':
            val = struct.unpack('<q', self.read_bytes(8))[0]
            return ('int64', val)
        elif type_code == 'g':
            val = struct.unpack('<d', self.read_bytes(8))[0]
            return ('float', val)
        elif type_code == 's':
            n = self.read_long()
            raw = self.read_bytes(n)
            s = deobfuscate_string(raw)
            return ('string', s)
        elif type_code == 't':
            n = self.read_long()
            raw = self.read_bytes(n)
            s = deobfuscate_string(raw)
            self.interned.append(s)
            return ('interned', s)
        elif type_code == 'R':
            idx = self.read_long()
            return ('stringref', self.interned[idx])
        elif type_code in ('(', '['):
            n = self.read_long()
            items = [self.read_object() for _ in range(n)]
            return ('tuple' if type_code == '(' else 'list', items)
        elif type_code == 'c':
            argcount = self.read_long()
            nlocals = self.read_long()
            stacksize = self.read_long()
            flags = self.read_long()
            code = self.read_object()
            consts = self.read_object()
            names = self.read_object()
            varnames = self.read_object()
            freevars = self.read_object()
            cellvars = self.read_object()
            filename = self.read_object()
            name = self.read_object()
            firstlineno = self.read_long()
            lnotab = self.read_object()
            return ('code', {
                'argcount': argcount, 'nlocals': nlocals, 'stacksize': stacksize,
                'flags': flags, 'code': code, 'consts': consts, 'names': names,
                'varnames': varnames, 'freevars': freevars, 'cellvars': cellvars,
                'filename': filename, 'name': name, 'firstlineno': firstlineno,
                'lnotab': lnotab
            })
        else:
            raise ValueError(f'Unknown type_code: {repr(type_code)} at pos {self.pos - 1}')

with open('redirect_decrypted.bin', 'rb') as f:
    data = f.read()

u = NeoXUnmarshaler(data)
obj = u.read_object()
print('SUCCESSFULLY UNMARSHALED!')
print('Object type:', obj[0])
print('Code filename:', obj[1]['filename'])
print('Code name:', obj[1]['name'])
print('Argcount:', obj[1]['argcount'], 'Stacksize:', obj[1]['stacksize'])
print('Consts count:', len(obj[1]['consts'][1]))
print('Names count:', len(obj[1]['names'][1]))
print('\nFirst 20 names:')
for n in obj[1]['names'][1][:20]:
    print('  ', n)
print('\nSample consts:')
for c in obj[1]['consts'][1][:15]:
    if c[0] in ('string', 'interned'):
        print('   str:', repr(c[1]))
    elif c[0] == 'code':
        print('   sub-code:', c[1]['name'], 'file:', c[1]['filename'])
    else:
        print('  ', c)
