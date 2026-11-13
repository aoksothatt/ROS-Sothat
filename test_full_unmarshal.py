import os, struct
from parse_redirect import deobfuscate_string

class FullNeoXUnmarshaler:
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
        elif type_code == '0':
            return ('NULL', None)
        elif type_code == 'i':
            val = self.read_long()
            return ('int', val)
        elif type_code == 'I':
            val = struct.unpack('<q', self.read_bytes(8))[0]
            return ('int64', val)
        elif type_code == 'f':
            n = self.read_byte()
            s = self.read_bytes(n)
            return ('float_str', s)
        elif type_code == 'g':
            val = struct.unpack('<d', self.read_bytes(8))[0]
            return ('float', val)
        elif type_code == 'l': # PyLong
            n = self.read_long()
            # abs(n) 2-byte digits
            digits = [struct.unpack('<H', self.read_bytes(2))[0] for _ in range(abs(n))]
            return ('long', (n, digits))
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
        elif type_code == 'u': # Unicode string
            n = self.read_long()
            raw = self.read_bytes(n)
            s = deobfuscate_string(raw)
            return ('unicode', s.decode('utf-8', errors='ignore'))
        elif type_code == 'R':
            idx = self.read_long()
            return ('stringref', self.interned[idx])
        elif type_code in ('(', '['):
            n = self.read_long()
            items = [self.read_object() for _ in range(n)]
            return ('tuple' if type_code == '(' else 'list', items)
        elif type_code in ('<', '>'):
            n = self.read_long()
            items = [self.read_object() for _ in range(n)]
            return ('set' if type_code == '<' else 'frozenset', items)
        elif type_code == '{':
            items = {}
            while True:
                k = self.read_object()
                if k[0] == 'NULL':
                    break
                v = self.read_object()
                items[str(k)] = v
            return ('dict', items)
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

# Test on unknown_0008
with open(r'extracted\scripts\unknown_0008_0x00a660d3.bin.raw', 'rb') as f:
    data = f.read()

u = FullNeoXUnmarshaler(data)
obj = u.read_object()
print('unknown_0008 successfully resolved!')
print('Filename:', obj[1]['filename'])
print('Name:', obj[1]['name'])
