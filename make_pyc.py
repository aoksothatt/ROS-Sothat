import struct
from parse_redirect import deobfuscate_string

def convert_raw_to_pyc(raw_data):
    # Output buffer starting with Python 2.7 pyc header
    # Magic for Python 2.7: 0x03 0xf3 0x0d 0x0a (62211)
    # Timestamp: 4 bytes (e.g. 0)
    out = bytearray(b'\x03\xf3\r\n\x00\x00\x00\x00')
    
    pos = 0
    L = len(raw_data)
    
    def read_byte():
        nonlocal pos
        b = raw_data[pos]
        pos += 1
        return b
        
    def read_bytes(n):
        nonlocal pos
        res = raw_data[pos:pos+n]
        pos += n
        return res
        
    def read_long():
        return struct.unpack('<i', read_bytes(4))[0]

    def process_object():
        nonlocal pos
        tc = chr(read_byte())
        out.append(ord(tc))
        
        if tc in ('N', 'T', 'F', '0'):
            return
        elif tc == 'i':
            val_bytes = read_bytes(4)
            out.extend(val_bytes)
        elif tc == 'I':
            val_bytes = read_bytes(8)
            out.extend(val_bytes)
        elif tc == 'f':
            flen = read_byte()
            out.append(flen)
            out.extend(read_bytes(flen))
        elif tc == 'g':
            out.extend(read_bytes(8))
        elif tc == 'y':
            out.extend(read_bytes(16))
        elif tc == 'l':
            n_bytes = read_bytes(4)
            out.extend(n_bytes)
            n = struct.unpack('<i', n_bytes)[0]
            out.extend(read_bytes(abs(n) * 2))
        elif tc in ('s', 't', 'u'):
            n_bytes = read_bytes(4)
            out.extend(n_bytes)
            n = struct.unpack('<i', n_bytes)[0]
            raw_s = read_bytes(n)
            clean_s = deobfuscate_string(raw_s)
            out.extend(clean_s)
        elif tc == 'R':
            out.extend(read_bytes(4))
        elif tc in ('(', '[', '<', '>'):
            n_bytes = read_bytes(4)
            out.extend(n_bytes)
            n = struct.unpack('<i', n_bytes)[0]
            for _ in range(n):
                process_object()
        elif tc == '{':
            while True:
                # peek next byte or process key
                # If key is '0', dict ends
                curr_b = raw_data[pos]
                if chr(curr_b) == '0':
                    read_byte()
                    out.append(ord('0'))
                    break
                process_object() # key
                process_object() # val
        elif tc == 'c':
            # argcount, nlocals, stacksize, flags
            out.extend(read_bytes(16))
            process_object() # code
            process_object() # consts
            process_object() # names
            process_object() # varnames
            process_object() # freevars
            process_object() # cellvars
            process_object() # filename
            process_object() # name
            # firstlineno
            out.extend(read_bytes(4))
            process_object() # lnotab
        else:
            raise ValueError(f"Unknown type_code: {repr(tc)} at pos {pos-1}")

    process_object()
    return bytes(out)

if __name__ == '__main__':
    # Test on redirect_decrypted.bin
    with open('redirect_decrypted.bin', 'rb') as f:
        raw = f.read()
    pyc_data = convert_raw_to_pyc(raw)
    with open('redirect.pyc', 'wb') as f:
        f.write(pyc_data)
    print(f'Wrote redirect.pyc ({len(pyc_data)} bytes)')
