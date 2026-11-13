import capstone
import struct

BINARY_PATH = "extracted/Payload/client.app/client"

def find_string_refs(target_vas):
    with open(BINARY_PATH, "rb") as f:
        # We know __TEXT is 0x100000000 to 0x10339c000
        # Let's search around Mercury code: 0x100910000 to 0x100935000
        start_va = 0x100910000
        end_va = 0x100935000
        f.seek(start_va - 0x100000000)
        code = f.read(end_va - start_va)
    
    md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
    md.detail = True
    
    # Track current adrp registers
    adrp_regs = {}
    
    print(f"Scanning 0x{start_va:x} - 0x{end_va:x} for string references...")
    for ins in md.disasm(code, start_va):
        if ins.mnemonic == 'adrp':
            reg = ins.operands[0].reg
            imm = ins.operands[1].imm
            adrp_regs[reg] = imm
        elif ins.mnemonic == 'add' and len(ins.operands) >= 3:
            dst = ins.operands[0].reg
            src = ins.operands[1].reg
            if src in adrp_regs and ins.operands[2].type == capstone.arm64.ARM64_OP_IMM:
                target = adrp_regs[src] + ins.operands[2].imm
                for tva in target_vas:
                    if target == tva:
                        print(f"0x{ins.address:08x}:  {ins.mnemonic} {ins.op_str} -> references 0x{target:08x}")
                if dst != src:
                    pass
                else:
                    adrp_regs[dst] = target

if __name__ == "__main__":
    targets = [
        0x1030a34d8, # Not enough data for first request offset
        0x1030a352c, # Not enough footers for fragment spec
        0x1030a3588, # Dropping fragment due to illegal bundle fragment count
        0x1030a3411, # illegal request for reliability
        0x1030a348b, # illegal once-off-reliable packet
        0x1030a3231, # ack count footer
        0x1030a307f, # indexed channel footer
        0x1030a2efc, # piggyback length
    ]
    find_string_refs(targets)
