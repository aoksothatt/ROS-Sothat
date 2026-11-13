import struct

def parse_macho(path):
    with open(path, "rb") as f:
        data = f.read(4096)
    magic = struct.unpack("<I", data[:4])[0]
    print(f"Magic: 0x{magic:08x}")
    cputype, cpusubtype, filetype, ncmds, sizeofcmds, flags = struct.unpack("<IIIIII", data[4:28])
    print(f"ncmds: {ncmds}, sizeofcmds: {sizeofcmds}")
    offset = 32
    for _ in range(ncmds):
        cmd, cmdsize = struct.unpack("<II", data[offset:offset+8])
        if cmd == 0x19: # LC_SEGMENT_64
            segname = data[offset+8:offset+24].rstrip(b'\x00').decode('ascii', errors='ignore')
            vmaddr, vmsize, fileoff, filesize = struct.unpack("<QQQQ", data[offset+24:offset+56])
            print(f"Segment: {segname:<16} vmaddr: 0x{vmaddr:016x} vmsize: 0x{vmsize:08x} fileoff: 0x{fileoff:08x} filesize: 0x{filesize:08x}")
        offset += cmdsize

if __name__ == "__main__":
    parse_macho("extracted/Payload/client.app/client")
