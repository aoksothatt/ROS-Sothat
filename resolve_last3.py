import os, struct
from parse_redirect import deobfuscate_string

class CleanUnmarshaler:
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
            return ('string', s)
        elif type_code == 'R': return ('stringref', self.interned[self.read_long()])
        elif type_code in ('(', '[', '<', '>'):
            return ('seq', [self.read_object() for _ in range(self.read_long())])
        elif type_code == '{':
            items = {}
            while True:
                k = self.read_object()
                if k[0] == 'NULL': break
                items[str(k)] = self.read_object()
            return ('dict', items)
        elif type_code == 'c':
            argcount, nlocals, stacksize, flags = self.read_long(), self.read_long(), self.read_long(), self.read_long()
            code, consts, names, varnames, freevars, cellvars = self.read_object(), self.read_object(), self.read_object(), self.read_object(), self.read_object(), self.read_object()
            filename, name = self.read_object(), self.read_object()
            firstlineno, lnotab = self.read_long(), self.read_object()
            return ('code', {'filename': filename, 'name': name})
        else:
            raise ValueError(f'Unknown type_code: {repr(type_code)} at pos {self.pos - 1}')

if __name__ == '__main__':
    out_dir = r'extracted\scripts'
    for name in ['unknown_1709_0x6b9f51e9.bin.raw', 'unknown_2619_0xa71ac4a0.bin.raw', 'unknown_3431_0xdc58bc3c.bin.raw']:
        p = os.path.join(out_dir, name)
        if os.path.exists(p):
            with open(p, 'rb') as f:
                data = f.read()
            u = CleanUnmarshaler(data)
            obj = u.read_object()
            raw_fn = obj[1]['filename'][1].decode('utf-8', errors='ignore').replace('\\', '/').lstrip('/')
            print(f'{name} -> {raw_fn}')
            dest = os.path.join(out_dir, raw_fn) + '.raw'
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, 'wb') as out_f:
                out_f.write(data)
            os.remove(p)
    print('Finished resolving last 3 files!')
