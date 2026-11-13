"""
Independent Reconstruction of Mercury Datagrams for Phase 6.2B.8.1 Audit
Uses raw cryptography Blowfish ECB and standard struct packing.
Does NOT import any modules from phase6B_8_local_gateway or phase6B_7_2_synthetic_research.
"""

import struct
from cryptography.hazmat.primitives.ciphers import Cipher, modes
from cryptography.hazmat.decrepit.ciphers.algorithms import Blowfish

# Master Synthetic Key (56 bytes)
KEY = b"ROS_SOTHAT_DETERMINISTIC_SYNTHETIC_BLOWFISH_SESSION_KEY!"
assert len(KEY) == 56

def independent_pbc_encrypt(key: bytes, plaintext: bytes) -> bytes:
    assert len(plaintext) % 8 == 0
    cipher = Cipher(Blowfish(key), modes.ECB())
    encryptor = cipher.encryptor()
    
    ciphertext = bytearray()
    prev_pt = None
    
    for offset in range(0, len(plaintext), 8):
        pt_block = plaintext[offset:offset+8]
        if prev_pt is None:
            # Block 0: P_0 ^ IV (IV = 0)
            xored = pt_block
        else:
            # Block i >= 1: P_i ^ P_(i-1)
            xored = bytes(a ^ b for a, b in zip(pt_block, prev_pt))
        
        c_block = encryptor.update(xored)
        ciphertext.extend(c_block)
        prev_pt = pt_block
        
    return bytes(ciphertext)

def independent_checksum(buf: bytes, csum_offset: int) -> int:
    # Zero field in-place
    mutable = bytearray(buf)
    struct.pack_into("<I", mutable, csum_offset, 0)
    
    # Align to 4-byte boundary
    pad = (4 - (len(mutable) % 4)) % 4
    mutable.extend(bytes(pad))
    
    csum = 0
    for offset in range(0, len(mutable), 4):
        dword = struct.unpack_from("<I", mutable, offset)[0]
        csum ^= dword
    return csum & 0xFFFFFFFF

# ==============================================================================
# Datagram 1: Channel 1 Initialization Request
# Flags: FLAG_CREATE_CHANNEL (0x0001) | FLAG_INDEXED_CHANNEL (0x0080) | 
#        FLAG_HAS_SEQUENCE_NUMBER (0x0004) | FLAG_HAS_CHECKSUM (0x0100) = 0x0185
# SeqNum: 1
# Channel ID: 1
# Payload: b'{"action": "INIT_CHANNEL", "session_id": "sess_01"}' (51 bytes)
# ==============================================================================
payload_1 = b'{"action": "INIT_CHANNEL", "session_id": "sess_01"}'
flags_1 = 0x0185
seq_num_1 = 1
channel_id_1 = 1

# Footers assembled in forward order:
# 1. SeqNum: <I
# 2. ChannelID: <I
# 3. Checksum placeholder: 4 zero bytes
footers_1 = bytearray()
footers_1.extend(struct.pack("<I", seq_num_1))
footers_1.extend(struct.pack("<I", channel_id_1))
footers_1.extend(b"\x00\x00\x00\x00")

raw_1 = bytearray(struct.pack("<H", flags_1)) + payload_1 + footers_1
raw_len_1 = len(raw_1)
csum_offset_1 = raw_len_1 - 4
csum_1 = independent_checksum(bytes(raw_1), csum_offset_1)
struct.pack_into("<I", raw_1, csum_offset_1, csum_1)

# Padding: 8 - (raw_len % 8)
pad_len_1 = 8 - (raw_len_1 % 8)
padded_1 = bytes(raw_1) + bytes(pad_len_1 - 1) + bytes([pad_len_1])
assert len(padded_1) % 8 == 0

ct_1 = independent_pbc_encrypt(KEY, padded_1)

print("--- DATAGRAM 1 (Init Request) ---")
print(f"Payload ({len(payload_1)}B): {payload_1}")
print(f"Flags: 0x{flags_1:04x}")
print(f"Raw Packet Length: {raw_len_1} bytes")
print(f"Computed Checksum: 0x{csum_1:08x}")
print(f"Raw Packet Hex: {bytes(raw_1).hex()}")
print(f"Pad Length: {pad_len_1} bytes (trailer: 0x{pad_len_1:02x})")
print(f"Padded Length: {len(padded_1)} bytes ({len(padded_1)//8} blocks)")
print(f"Padded Packet Hex: {padded_1.hex()}")
print(f"Ciphertext Hex: {ct_1.hex()}")

# ==============================================================================
# Datagram 2: Application Message on Channel 1
# Flags: FLAG_ON_CHANNEL (0x0020) | FLAG_INDEXED_CHANNEL (0x0080) |
#        FLAG_HAS_SEQUENCE_NUMBER (0x0004) | FLAG_HAS_CHECKSUM (0x0100) = 0x01A4
# SeqNum: 2
# Channel ID: 1
# Payload: b'PING_MESSAGE_ON_CHANNEL_1' (25 bytes)
# ==============================================================================
payload_2 = b"PING_MESSAGE_ON_CHANNEL_1"
flags_2 = 0x01A4
seq_num_2 = 2
channel_id_2 = 1

footers_2 = bytearray()
footers_2.extend(struct.pack("<I", seq_num_2))
footers_2.extend(struct.pack("<I", channel_id_2))
footers_2.extend(b"\x00\x00\x00\x00")

raw_2 = bytearray(struct.pack("<H", flags_2)) + payload_2 + footers_2
raw_len_2 = len(raw_2)
csum_offset_2 = raw_len_2 - 4
csum_2 = independent_checksum(bytes(raw_2), csum_offset_2)
struct.pack_into("<I", raw_2, csum_offset_2, csum_2)

pad_len_2 = 8 - (raw_len_2 % 8)
padded_2 = bytes(raw_2) + bytes(pad_len_2 - 1) + bytes([pad_len_2])
assert len(padded_2) % 8 == 0

ct_2 = independent_pbc_encrypt(KEY, padded_2)

print("\n--- DATAGRAM 2 (Application Message) ---")
print(f"Payload ({len(payload_2)}B): {payload_2}")
print(f"Flags: 0x{flags_2:04x}")
print(f"Raw Packet Length: {raw_len_2} bytes")
print(f"Computed Checksum: 0x{csum_2:08x}")
print(f"Raw Packet Hex: {bytes(raw_2).hex()}")
print(f"Pad Length: {pad_len_2} bytes (trailer: 0x{pad_len_2:02x})")
print(f"Padded Length: {len(padded_2)} bytes ({len(padded_2)//8} blocks)")
print(f"Padded Packet Hex: {padded_2.hex()}")
print(f"Ciphertext Hex: {ct_2.hex()}")
