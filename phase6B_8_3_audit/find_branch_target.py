import capstone

BINARY_PATH = "extracted/Payload/client.app/client"

def find_branches_to(target_va, start_va, end_va):
    with open(BINARY_PATH, "rb") as f:
        f.seek(start_va - 0x100000000)
        raw = f.read(end_va - start_va)
    md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
    md.detail = True
    for ins in md.disasm(raw, start_va):
        for op in ins.operands:
            if op.type == capstone.arm64.ARM64_OP_IMM and op.imm == target_va:
                print(f"0x{ins.address:08x}:  {ins.mnemonic:<8} {ins.op_str}")

print("=== Branches to 0x100923974 ===")
find_branches_to(0x100923974, 0x100922800, 0x100923974)
