import capstone

BINARY_PATH = "extracted/Payload/client.app/client"

def dump_disasm(start_va, end_va):
    with open(BINARY_PATH, "rb") as f:
        file_off = start_va - 0x100000000
        f.seek(file_off)
        raw = f.read(end_va - start_va)
    
    md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
    lines = []
    for ins in md.disasm(raw, start_va):
        lines.append(f"0x{ins.address:08x}:  {ins.mnemonic:<8} {ins.op_str}")
    return "\n".join(lines)

if __name__ == "__main__":
    dis = dump_disasm(0x100922c00, 0x100923400)
    with open("phase6B_8_2_audit/disasm_process_filtered_packet_part2.txt", "w") as f:
        f.write(dis)
    print(f"Dumped {dis.count(chr(10))} lines")
