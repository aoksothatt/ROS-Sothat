"""
Phase 6.2B.8.2 - Investigation F: Independent Golden Vector Audit
Strictly isolated script using fixed literal golden vectors.
Does not import from phase6B_8_local_gateway or use any gateway helper functions.
"""

import struct
from cryptography.hazmat.primitives.ciphers import Cipher, modes
from cryptography.hazmat.decrepit.ciphers.algorithms import Blowfish

# Master Synthetic Key
KEY = b"ROS_SOTHAT_DETERMINISTIC_SYNTHETIC_BLOWFISH_SESSION_KEY!"

# Fixed Literal Golden Values from Phase 6.2B.8.1 Report
EXPECTED_CT_1_HEX = (
    "8aff37d58113b1a118aac47447b3722eb6a458cd99c422edbc26534e6dde6eeb"
    "2993ef333f5a7096f9287dca9ed23679b5829c275d42143e0f246c5997465409"
    "e0f6923d63f0cdbf"
)
EXPECTED_CSUM_1 = 0x034616a1

EXPECTED_CT_2_HEX = (
    "74f26a69d5ba69f6953bf0853339d0e9c8a2ad12404d3c2fe833d666c0acb182"
    "f7488878f17fa456"
)
EXPECTED_CSUM_2 = 0x043f1eab

def independent_block_pbc_encrypt(key: bytes, plaintext: bytes):
    assert len(plaintext) % 8 == 0
    cipher = Cipher(Blowfish(key), modes.ECB())
    encryptor = cipher.encryptor()
    
    blocks_in = []
    blocks_xored = []
    blocks_ct = []
    
    prev_pt = None
    for offset in range(0, len(plaintext), 8):
        pt_block = plaintext[offset:offset+8]
        blocks_in.append(pt_block)
        
        if prev_pt is None:
            # Block 0: IV = 0
            xored = pt_block
        else:
            # Block i >= 1: P_i ^ P_(i-1)
            xored = bytes(a ^ b for a, b in zip(pt_block, prev_pt))
            
        blocks_xored.append(xored)
        c_block = encryptor.update(xored)
        blocks_ct.append(c_block)
        prev_pt = pt_block
        
    return b"".join(blocks_ct), blocks_in, blocks_xored, blocks_ct

def independent_csum(data: bytes, csum_offset: int) -> int:
    b = bytearray(data)
    struct.pack_into("<I", b, csum_offset, 0)
    pad = (4 - (len(b) % 4)) % 4
    b.extend(bytes(pad))
    s = 0
    for off in range(0, len(b), 4):
        s ^= struct.unpack_from("<I", b, off)[0]
    return s & 0xFFFFFFFF

def run_audit():
    print("=" * 70)
    print("PHASE 6.2B.8.2 — INDEPENDENT GOLDEN VECTOR VERIFICATION")
    print("=" * 70)
    
    # Check 1: Vector 1 Reconstruction
    print("\n--- VECTOR 1 (Channel 1 Init Request) ---")
    payload_1 = b'{"action": "INIT_CHANNEL", "session_id": "sess_01"}'
    flags_1 = 0x0185
    seq_1 = 1
    chan_1 = 1
    
    raw_1 = bytearray()
    raw_1.extend(struct.pack("<H", flags_1))
    raw_1.extend(payload_1)
    raw_1.extend(struct.pack("<I", seq_1))
    raw_1.extend(struct.pack("<I", chan_1))
    raw_1.extend(b"\x00\x00\x00\x00") # checksum placeholder
    
    print(f"Raw Input Length: {len(raw_1)} bytes (Expected: 65 bytes)")
    assert len(raw_1) == 65
    
    # Recalculate checksum
    csum_1 = independent_csum(bytes(raw_1), len(raw_1) - 4)
    print(f"Recalculated Checksum: 0x{csum_1:08x} (Expected: 0x{EXPECTED_CSUM_1:08x})")
    assert csum_1 == EXPECTED_CSUM_1
    struct.pack_into("<I", raw_1, len(raw_1) - 4, csum_1)
    
    # Recalculate padding
    pad_len_1 = 8 - (len(raw_1) % 8)
    padded_1 = bytes(raw_1) + bytes(pad_len_1 - 1) + bytes([pad_len_1])
    print(f"Padded Length: {len(padded_1)} bytes (Expected: 72 bytes, 9 blocks)")
    assert len(padded_1) == 72
    assert pad_len_1 == 7
    
    # Encrypt blocks
    ct_1, in_1, xor_1, out_1 = independent_block_pbc_encrypt(KEY, padded_1)
    print(f"Ciphertext Length: {len(ct_1)} bytes (Expected: 72 bytes)")
    assert len(ct_1) == 72
    print(f"Ciphertext Hex: {ct_1.hex()}")
    assert ct_1.hex() == EXPECTED_CT_1_HEX
    print("Vector 1 Result: 100% BIT-FOR-BIT MATCH AGAINST FIXED LITERAL GOLDEN VECTOR")
    
    for idx, (b_in, b_xor, b_out) in enumerate(zip(in_1, xor_1, out_1)):
        print(f"  Block {idx}: P={b_in.hex()} XOR={b_xor.hex()} -> C={b_out.hex()}")
        
    # Check 2: Vector 2 Reconstruction
    print("\n--- VECTOR 2 (Application Message on Channel 1) ---")
    payload_2 = b"PING_MESSAGE_ON_CHANNEL_1"
    flags_2 = 0x01A4
    seq_2 = 2
    chan_2 = 1
    
    raw_2 = bytearray()
    raw_2.extend(struct.pack("<H", flags_2))
    raw_2.extend(payload_2)
    raw_2.extend(struct.pack("<I", seq_2))
    raw_2.extend(struct.pack("<I", chan_2))
    raw_2.extend(b"\x00\x00\x00\x00")
    
    print(f"Raw Input Length: {len(raw_2)} bytes (Expected: 39 bytes)")
    assert len(raw_2) == 39
    
    csum_2 = independent_csum(bytes(raw_2), len(raw_2) - 4)
    print(f"Recalculated Checksum: 0x{csum_2:08x} (Expected: 0x{EXPECTED_CSUM_2:08x})")
    assert csum_2 == EXPECTED_CSUM_2
    struct.pack_into("<I", raw_2, len(raw_2) - 4, csum_2)
    
    pad_len_2 = 8 - (len(raw_2) % 8)
    padded_2 = bytes(raw_2) + bytes(pad_len_2 - 1) + bytes([pad_len_2])
    print(f"Padded Length: {len(padded_2)} bytes (Expected: 40 bytes, 5 blocks)")
    assert len(padded_2) == 40
    assert pad_len_2 == 1
    
    ct_2, in_2, xor_2, out_2 = independent_block_pbc_encrypt(KEY, padded_2)
    print(f"Ciphertext Length: {len(ct_2)} bytes (Expected: 40 bytes)")
    assert len(ct_2) == 40
    print(f"Ciphertext Hex: {ct_2.hex()}")
    assert ct_2.hex() == EXPECTED_CT_2_HEX
    print("Vector 2 Result: 100% BIT-FOR-BIT MATCH AGAINST FIXED LITERAL GOLDEN VECTOR")
    
    for idx, (b_in, b_xor, b_out) in enumerate(zip(in_2, xor_2, out_2)):
        print(f"  Block {idx}: P={b_in.hex()} XOR={b_xor.hex()} -> C={b_out.hex()}")

if __name__ == "__main__":
    run_audit()
