def simulate_csum_prep(checksum_offset):
    # Instructions:
    # 0x100922a58: add x12, x19, #0x64  (x12 = packet_data + 4)
    # 0x100922a5c: cmp x10, x12          (compare checksum_ptr with packet_data + 4)
    # 0x100922a60: csel x12, x10, x12, hi (x12 = max(checksum_ptr, packet_data + 4))
    # 0x100922a64: mvn x13, x19          (x13 = ~x19 = -x19 - 1)
    # 0x100922a68: add x12, x12, x13     (x12 = x12 - x19 - 1)
    # 0x100922a6c: sub x12, x12, #0x60   (x12 = offset_from_packet_data - 1)
    # 0x100922a70: cmp x12, #0x1c        (compare with 28)
    # 0x100922a74: b.hs NEON_LOOP
    offset_from_data = checksum_offset
    x12 = max(offset_from_data, 4) - 1
    print(f"checksum_offset: {checksum_offset}, x12 (offset-1): {x12}, uses_neon: {x12 >= 0x1c}")
    
    # NEON:
    # 0x100922bdc: lsr x12, x12, #2   (dwords - 1)
    # 0x100922be0: add x13, x12, #1   (total dwords)
    # 0x100922be4: and x14, x13, #0x7ffffffffff8 (round down to mult of 8)
    # 0x100922be8: add x12, x28, x14, lsl #2     (resume ptr = packet_data + x14 * 4)
    dword_count = (x12 >> 2) + 1
    mult8_dwords = dword_count & (~7)
    neon_bytes = mult8_dwords * 4
    scalar_resume_offset = neon_bytes
    print(f"dword_count: {dword_count}, mult8: {mult8_dwords}, neon_bytes: {neon_bytes}, scalar_resume: {scalar_resume_offset}")

    # Scalar loop:
    # 0x100922c34: ldr w13, [x12], #4
    # 0x100922c38: eor w22, w13, w22
    # 0x100922c3c: cmp x12, x10
    # 0x100922c40: b.lo loop
    cur = scalar_resume_offset
    scalar_steps = []
    while cur < offset_from_data:
        scalar_steps.append((cur, cur + 4))
        cur += 4
    print(f"Scalar steps: {scalar_steps}, final cur: {cur}, reaches x10: {cur == offset_from_data}")

for off in [60, 61, 64, 36, 40]:
    print(f"\n--- Testing offset {off} ---")
    simulate_csum_prep(off)
