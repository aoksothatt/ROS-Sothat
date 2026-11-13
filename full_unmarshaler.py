import struct
from parse_redirect import deobfuscate_string

class FullUnmarshaler:
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
        return struct.unpack('<i', self.read_bytes(4))[0]

    def read_object(self):
        type_code = chr(self.read_byte())
        if type_code == 'N': return ('None', None)
        elif type_code == 'T': return ('True', True)
        elif type_code == 'F': return ('False', False)
        elif type_code == '0': return ('NULL', None)
        elif type_code == 'i': return ('int', self.read_long())
        elif type_code == 'I': return ('int64', struct.unpack('<q', self.read_bytes(8))[0])
        elif type_code == 'f': return ('float_str', self.read_bytes(self.read_byte()))
        elif type_code == 'g': return ('float', struct.unpack('<d', self.read_bytes(8))[0])
        elif type_code == 'y': return ('complex', struct.unpack('<dd', self.read_bytes(16)))
        elif type_code == 'l':
            n = self.read_long()
            return ('long', [struct.unpack('<H', self.read_bytes(2))[0] for _ in range(abs(n))])
        elif type_code in ('s', 't', 'u'):
            n = self.read_long()
            s = deobfuscate_string(self.read_bytes(n))
            if type_code == 't': self.interned.append(s)
            return ('string' if type_code != 'u' else 'unicode', s)
        elif type_code == 'R': return ('stringref', self.interned[self.read_long()])
        elif type_code in ('(', '['):
            return ('tuple' if type_code == '(' else 'list', [self.read_object() for _ in range(self.read_long())])
        elif type_code in ('<', '>'):
            return ('set' if type_code == '<' else 'frozenset', [self.read_object() for _ in range(self.read_long())])
        elif type_code == '{':
            items = {}
            while True:
                k = self.read_object()
                if k[0] == 'NULL': break
                items[str(k)] = self.read_object()
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

def load_script(path):
    with open(path, 'rb') as f:
        u = FullUnmarshaler(f.read())
        return u.read_object()[1]
