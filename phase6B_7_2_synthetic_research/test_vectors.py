"""
Deterministic Synthetic Cryptographic & Framing Test Vectors
Phase 6.2B.7.2 - Research & Verification

Contains reproducible synthetic test vectors for:
1. Blowfish Plaintext Block Chaining (PBC) vs standard CBC
2. Single-Byte Trailer Padding across critical boundary lengths
3. Mercury 32-bit XOR Checksum calculation
4. End-to-End Combined Mercury Datagram Pipeline
"""

import struct
from pbc_cipher import BlowfishPBC
from padding import SingleByteTrailerPadding
from checksum import MercuryChecksum
from pipeline import MercurySyntheticPipeline, MercuryPacketFlags

# Deterministic 56-byte synthetic session key (448 bits)
SYNTHETIC_SESSION_KEY_56 = (
    b"ROS_SOTHAT_DETERMINISTIC_SYNTHETIC_BLOWFISH_SESSION_KEY!"
)
assert len(SYNTHETIC_SESSION_KEY_56) == 56

# Secondary 32-byte synthetic key (256 bits)
SYNTHETIC_SESSION_KEY_32 = b"SYNTHETIC_32_BYTE_BLOWFISH_KEY!!"
assert len(SYNTHETIC_SESSION_KEY_32) == 32


# ==============================================================================
# 1. Blowfish PBC Deterministic Test Vectors
# ==============================================================================
cipher_pbc = BlowfishPBC(SYNTHETIC_SESSION_KEY_56)

# Vector 1.1: Single-block (8 bytes) -> PBC and CBC are IDENTICAL
VEC_PBC_1BLOCK_PLAINTEXT = b"BLOCK_01"
VEC_PBC_1BLOCK_CIPHERTEXT = cipher_pbc.encrypt(VEC_PBC_1BLOCK_PLAINTEXT)
VEC_CBC_1BLOCK_CIPHERTEXT = cipher_pbc.encrypt_standard_cbc(VEC_PBC_1BLOCK_PLAINTEXT)
assert VEC_PBC_1BLOCK_CIPHERTEXT == VEC_CBC_1BLOCK_CIPHERTEXT

# Vector 1.2: Two-block (16 bytes) -> Block 0 matches, Block 1 DIVERGES
VEC_PBC_2BLOCK_PLAINTEXT = b"BLOCK_01" + b"BLOCK_02"
VEC_PBC_2BLOCK_CIPHERTEXT = cipher_pbc.encrypt(VEC_PBC_2BLOCK_PLAINTEXT)
VEC_CBC_2BLOCK_CIPHERTEXT = cipher_pbc.encrypt_standard_cbc(VEC_PBC_2BLOCK_PLAINTEXT)
assert VEC_PBC_2BLOCK_CIPHERTEXT[:8] == VEC_CBC_2BLOCK_CIPHERTEXT[:8]
assert VEC_PBC_2BLOCK_CIPHERTEXT[8:] != VEC_CBC_2BLOCK_CIPHERTEXT[8:]

# Vector 1.3: Three-block (24 bytes)
VEC_PBC_3BLOCK_PLAINTEXT = b"BLOCK_01" + b"BLOCK_02" + b"BLOCK_03"
VEC_PBC_3BLOCK_CIPHERTEXT = cipher_pbc.encrypt(VEC_PBC_3BLOCK_PLAINTEXT)
VEC_CBC_3BLOCK_CIPHERTEXT = cipher_pbc.encrypt_standard_cbc(VEC_PBC_3BLOCK_PLAINTEXT)

# Vector 1.4: Four-block (32 bytes)
VEC_PBC_4BLOCK_PLAINTEXT = b"BLOCK_01" + b"BLOCK_02" + b"BLOCK_03" + b"BLOCK_04"
VEC_PBC_4BLOCK_CIPHERTEXT = cipher_pbc.encrypt(VEC_PBC_4BLOCK_PLAINTEXT)
VEC_CBC_4BLOCK_CIPHERTEXT = cipher_pbc.encrypt_standard_cbc(VEC_PBC_4BLOCK_PLAINTEXT)


# ==============================================================================
# 2. Single-Byte Trailer Padding Boundary Vectors
# ==============================================================================
PADDING_BOUNDARY_LENGTHS = [0, 1, 7, 8, 9, 15, 16, 17, 31, 32]
PADDING_VECTORS = []

for length in PADDING_BOUNDARY_LENGTHS:
    raw_bytes = bytes([(i % 256) for i in range(length)])
    padded_zero = SingleByteTrailerPadding.pad(raw_bytes, slack_mode="zero")
    padded_rand = SingleByteTrailerPadding.pad(raw_bytes, slack_mode="random")
    padded_pkcs = SingleByteTrailerPadding.pad(raw_bytes, slack_mode="pkcs7")
    pad_len = SingleByteTrailerPadding.calculate_pad_length(length)
    
    PADDING_VECTORS.append({
        "raw_len": length,
        "pad_len": pad_len,
        "padded_len": len(padded_zero),
        "trailer_byte": padded_zero[-1],
        "padded_zero_hex": padded_zero.hex(),
        "padded_rand_hex": padded_rand.hex(),
        "padded_pkcs_hex": padded_pkcs.hex()
    })


# ==============================================================================
# 3. Mercury 32-bit XOR Checksum Vectors
# ==============================================================================
CHECKSUM_VECTORS = []

# Vector 3.1: Minimal packet (Flags = 0x0100 + Checksum = 4 bytes) -> Total 6 bytes
pkt_minimal = bytearray(struct.pack("<H", MercuryPacketFlags.FLAG_HAS_CHECKSUM) + b"\x00\x00\x00\x00")
MercuryChecksum.inject(pkt_minimal)
is_valid_min, comp_min, stored_min = MercuryChecksum.verify(bytes(pkt_minimal))
CHECKSUM_VECTORS.append({
    "desc": "Minimal Packet (Flags + Checksum only, 6 bytes)",
    "packet_hex": pkt_minimal.hex(),
    "checksum": stored_min,
    "is_valid": is_valid_min
})

# Vector 3.2: Packet with Body Payload
pkt_body = bytearray(
    struct.pack("<H", MercuryPacketFlags.FLAG_HAS_CHECKSUM) +
    b"SYNTHETIC_MERCURY_PAYLOAD_BODY" +
    b"\x00\x00\x00\x00"
)
MercuryChecksum.inject(pkt_body)
is_valid_body, comp_body, stored_body = MercuryChecksum.verify(bytes(pkt_body))
CHECKSUM_VECTORS.append({
    "desc": "Packet with Body Payload (36 bytes)",
    "packet_hex": pkt_body.hex(),
    "checksum": stored_body,
    "is_valid": is_valid_body
})

# Vector 3.3: Packet with Sequence Number and Channel ID Footers
pipeline_test = MercurySyntheticPipeline(SYNTHETIC_SESSION_KEY_56)
pkt_footers = pipeline_test.assemble_plaintext_packet(
    payload=b"MESSAGE_BUNDLE_DATA",
    flags=0,
    seq_num=0x000004D2,       # 1234
    channel_id=0x01000100,    # Channel ID
    enable_checksum=True
)
is_valid_foot, comp_foot, stored_foot = MercuryChecksum.verify(bytes(pkt_footers))
CHECKSUM_VECTORS.append({
    "desc": "Packet with Footers (SeqNum + Channel ID + Checksum)",
    "packet_hex": pkt_footers.hex(),
    "checksum": stored_foot,
    "is_valid": is_valid_foot
})


# ==============================================================================
# 4. Combined End-to-End Pipeline Vectors
# ==============================================================================
COMBINED_VECTORS = []

# Combined Vector 4.1: Synthetic Login Request Datagram
login_payload = b'{"account":"test_user","token":"syn_token_123"}'
ct_login = pipeline_test.send_pipeline(
    payload=login_payload,
    flags=0,
    seq_num=1001,
    channel_id=1,
    enable_checksum=True,
    slack_mode="zero"
)
rec_login = pipeline_test.receive_pipeline(ct_login)
assert rec_login["payload"] == login_payload
assert rec_login["sequence_number"] == 1001
assert rec_login["channel_id"] == 1

COMBINED_VECTORS.append({
    "name": "Synthetic Login Request Datagram",
    "payload": login_payload.decode("latin1"),
    "seq_num": 1001,
    "channel_id": 1,
    "ciphertext_len": len(ct_login),
    "ciphertext_hex": ct_login.hex(),
    "recovered_checksum": hex(rec_login["checksum"]),
    "status": "VERIFIED"
})

# Combined Vector 4.2: Synthetic Ping / Keepalive Datagram (Empty Payload)
ct_ping = pipeline_test.send_pipeline(
    payload=b"",
    flags=0,
    seq_num=500,
    channel_id=None,
    enable_checksum=True,
    slack_mode="zero"
)
rec_ping = pipeline_test.receive_pipeline(ct_ping)
assert rec_ping["payload"] == b""
assert rec_ping["sequence_number"] == 500

COMBINED_VECTORS.append({
    "name": "Synthetic Ping Datagram (Zero Payload)",
    "payload": "",
    "seq_num": 500,
    "channel_id": None,
    "ciphertext_len": len(ct_ping),
    "ciphertext_hex": ct_ping.hex(),
    "recovered_checksum": hex(rec_ping["checksum"]),
    "status": "VERIFIED"
})
