import zipfile, struct

with zipfile.ZipFile('RoS-Legacy-iOS.ipa') as z:
    client_data = z.read('Payload/client.app/client')

magic = client_data[:4]
cputype, cpusubtype, filetype, ncmds, sizeofcmds, flags = struct.unpack('<IIIIII', client_data[4:28])

offset = 32
sections = []
for _ in range(ncmds):
    cmd, cmdsz = struct.unpack('<II', client_data[offset:offset+8])
    if cmd == 0x19: # LC_SEGMENT_64
        segname = client_data[offset+8:offset+24].rstrip(b'\x00').decode('latin1')
        vmaddr, vmsize, fileoff, filesize, maxprot, initprot, nsects, flags = struct.unpack('<QQQQIIII', client_data[offset+24:offset+72])
        sect_offset = offset + 72
        for s in range(nsects):
            s_sectname = client_data[sect_offset:sect_offset+16].rstrip(b'\x00').decode('latin1')
            s_segname = client_data[sect_offset+16:sect_offset+32].rstrip(b'\x00').decode('latin1')
            s_addr, s_size, s_offset = struct.unpack('<QQI', client_data[sect_offset+32:sect_offset+52])
            sections.append((s_segname, s_sectname, s_addr, s_size, s_offset))
            sect_offset += 80
    offset += cmdsz

for seg, sect, addr, size, off in sections:
    if 'cstring' in sect or 'const' in sect or 'data' in sect:
        print(f'{seg:<10} {sect:<20} addr=0x{addr:016x} off=0x{off:08x} size=0x{size:08x}')
