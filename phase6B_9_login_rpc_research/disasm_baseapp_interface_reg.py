import capstone
import struct

with open('extracted/Payload/client.app/client', 'rb') as f:
    data = f.read()

start_va = 0x1008cde80
end_va = 0x1008ce300

start_off = start_va - 0x100000000
code = data[start_off:start_off + (end_va - start_va)]

md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)

for i in md.disasm(code, start_va):
    print("0x%x: %s %s" % (i.address, i.mnemonic, i.op_str))
