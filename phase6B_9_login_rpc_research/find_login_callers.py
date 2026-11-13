import struct
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM

CLIENT_PATH = "extracted/Payload/client.app/client"

def parse_macho(path):
    with open(path, "rb") as f:
        data = f.read()
    magic = struct.unpack_from("<I", data, 0)[0]
    assert magic == 0xfeedfacf, f"Invalid magic: {hex(magic)}"
    ncmds = struct.unpack_from("<I", data, 16)[0]
    offset = 32
    segments = []
    for _ in range(ncmds):
        cmd, cmdsize = struct.unpack_from("<II", data, offset)
        if cmd == 0x19: # LC_SEGMENT_64
            segname = data[offset+8:offset+24].split(b"\x00")[0].decode("latin1")
            vmaddr, vmsize, fileoff, filesize = struct.unpack_from("<QQQQ", data, offset+24)
            segments.append((segname, vmaddr, vmsize, fileoff, filesize))
        offset += cmdsize
    return data, segments

def vm_to_file(vmaddr, segments):
    for segname, seg_vm, seg_vmsize, fileoff, filesize in segments:
        if seg_vm <= vmaddr < seg_vm + seg_vmsize:
            return fileoff + (vmaddr - seg_vm)
    return None

data, segments = parse_macho(CLIENT_PATH)
print("Parsed segments:", [(s[0], hex(s[1]), hex(s[2])) for s in segments])

# Target 1: PublicKeyCipher::encrypt is at 0x100927c20
# Target 2: PublicKeyCipher::setKey is at 0x100927a20
# Find callers in __TEXT segment
text_seg = [s for s in segments if s[0] == "__TEXT"][0]
segname, vmaddr, vmsize, fileoff, filesize = text_seg
text_bytes = data[fileoff : fileoff + filesize]

md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
md.detail = True

target_encrypt = 0x100927c20
target_setkey = 0x100927a20

print(f"Scanning __TEXT ({hex(vmaddr)} - {hex(vmaddr + filesize)}) for calls to 0x{target_encrypt:x} and 0x{target_setkey:x}...")

callers_encrypt = []
callers_setkey = []

# Scan 4-byte aligned instructions
for i in range(0, filesize - 4, 4):
    insn_bytes = text_bytes[i : i + 4]
    insn_val = struct.unpack("<I", insn_bytes)[0]
    # Check for bl instruction: opcode 0x94000000 mask 0xFC000000
    if (insn_val & 0xFC000000) == 0x94000000:
        imm26 = insn_val & 0x03FFFFFF
        if imm26 & 0x02000000:
            imm26 -= 0x04000000
        target = vmaddr + i + (imm26 << 2)
        if target == target_encrypt:
            callers_encrypt.append(vmaddr + i)
        elif target == target_setkey:
            callers_setkey.append(vmaddr + i)

print(f"Found {len(callers_encrypt)} callers for PublicKeyCipher::encrypt:")
for c in callers_encrypt:
    print(f"  0x{c:08x}")

print(f"Found {len(callers_setkey)} callers for PublicKeyCipher::setKey:")
for c in callers_setkey:
    print(f"  0x{c:08x}")
