import struct

def native_arm64_checksum(packet_data: bytes, csum_offset: int) -> int:
    """
    Simulates EXACT bit-for-bit ARM64 instructions of
    neox::bwclient::Mercury::Nub::processFilteredPacket (0x100922a38 - 0x100922c44)
    """
    buf = bytearray(packet_data)
    # 0x100922a54: str wzr, [x10]
    struct.pack_into("<I", buf, csum_offset, 0)
    
    # 0x100922a58 - 0x100922a6c:
    # x12 = csum_offset - 1
    w9 = csum_offset
    x12 = max(w9, 4) - 1
    
    if x12 >= 0x1c:
        # NEON path:
        # 0x100922bdc: lsr x12, x12, #2
        x12_dwords = x12 >> 2
        # 0x100922be0: add x13, x12, #1
        x13 = x12_dwords + 1
        # 0x100922be4: and x14, x13, #0x7ffffffffff8
        x14 = x13 & ~7
        # 0x100922be8: add x12, x28, x14, lsl #2
        scalar_resume = x14 * 4
        
        # NEON SIMD XOR:
        # v0 and v1 each 16 bytes
        v0 = bytearray(16)
        v1 = bytearray(16)
        neon_bytes = x14 * 4
        for i in range(0, neon_bytes, 32):
            q2 = buf[i:i+16]
            q3 = buf[i+16:i+32]
            for j in range(16):
                v0[j] ^= q2[j]
                v1[j] ^= q3[j]
        
        # Folding:
        # 0x100922c14: eor v0.16b, v1.16b, v0.16b
        for j in range(16):
            v0[j] ^= v1[j]
        # 0x100922c18: dup v1.2d, v0.d[1]
        # 0x100922c1c: eor v0.16b, v0.16b, v1.16b
        d0 = struct.unpack("<Q", v0[:8])[0]
        d1 = struct.unpack("<Q", v0[8:16])[0]
        d_folded = d0 ^ d1
        
        # 0x100922c20: dup v1.4s, v0.s[1]
        # 0x100922c24: eor v0.16b, v0.16b, v1.16b
        s0 = d_folded & 0xFFFFFFFF
        s1 = (d_folded >> 32) & 0xFFFFFFFF
        w22 = s0 ^ s1
        
        # 0x100922c2c: cmp x13, x14
        # 0x100922c30: b.eq 0x100922c44
        cur_ptr = scalar_resume
    else:
        w22 = 0
        cur_ptr = 0
        
    # Scalar loop:
    # 0x100922c34: ldr w13, [x12], #4
    # 0x100922c38: eor w22, w13, w22
    # 0x100922c3c: cmp x12, x10
    # 0x100922c40: b.lo 0x100922c34
    while cur_ptr < csum_offset:
        # read 32-bit word
        word_bytes = buf[cur_ptr:cur_ptr+4]
        if len(word_bytes) < 4:
            word_bytes = word_bytes.ljust(4, b'\x00')
        w13 = struct.unpack("<I", word_bytes)[0]
        w22 ^= w13
        cur_ptr += 4
        
    return w22 & 0xFFFFFFFF

# Now let's test Datagram 1 and Datagram 2 from phase6B_8_1_audit
from independent_reconstruction import raw_1, csum_offset_1, csum_1, raw_2, csum_offset_2, csum_2

arm64_csum_1 = native_arm64_checksum(raw_1, csum_offset_1)
print(f"Datagram 1 Checksum: Expected 0x{csum_1:08x}, ARM64 native got: 0x{arm64_csum_1:08x}, Match: {csum_1 == arm64_csum_1}")

arm64_csum_2 = native_arm64_checksum(raw_2, csum_offset_2)
print(f"Datagram 2 Checksum: Expected 0x{csum_2:08x}, ARM64 native got: 0x{arm64_csum_2:08x}, Match: {csum_2 == arm64_csum_2}")
