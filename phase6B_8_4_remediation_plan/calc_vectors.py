import struct
from cryptography.hazmat.primitives.ciphers import Cipher, modes
from cryptography.hazmat.decrepit.ciphers.algorithms import Blowfish

KEY = b"ROS_SOTHAT_DETERMINISTIC_SYNTHETIC_BLOWFISH_SESSION_KEY!"
assert len(KEY) == 56

def pbc_encrypt(key, pt):
    cipher = Cipher(Blowfish(key), modes.ECB())
    enc = cipher.encryptor()
    ct = bytearray()
    prev = None
    for i in range(0, len(pt), 8):
        blk = pt[i:i+8]
        xored = blk if prev is None else bytes(a ^ b for a, b in zip(blk, prev))
        ct.extend(enc.update(xored))
        prev = blk
    return bytes(ct)

def calc_csum(buf, offset):
    m = bytearray(buf)
    struct.pack_into("<I", m, offset, 0)
    pad = (4 - (len(m) % 4)) % 4
    m.extend(bytes(pad))
    csum = 0
    for i in range(0, len(m), 4):
        csum ^= struct.unpack_from("<I", m, i)[0]
    return csum & 0xFFFFFFFF

# Vector A: Unit Test 3 with corrected flag 0x01C0
p_a = b'{"account":"test_user","token":"syn_token_123"}'
raw_a = bytearray(struct.pack("<H", 0x01C0)) + p_a + struct.pack("<I", 1001) + struct.pack("<I", 1) + b"\x00\x00\x00\x00"
csum_a = calc_csum(bytes(raw_a), len(raw_a)-4)
struct.pack_into("<I", raw_a, len(raw_a)-4, csum_a)
pad_a = 8 - (len(raw_a) % 8)
padded_a = bytes(raw_a) + bytes(pad_a - 1) + bytes([pad_a])
ct_a = pbc_encrypt(KEY, padded_a)
print("VECTOR A (Login 0x01C0):")
print(f"  raw_len: {len(raw_a)}")
print(f"  csum: 0x{csum_a:08x}")
print(f"  padded_len: {len(padded_a)}")
print(f"  pad_trailer: 0x{padded_a[-1]:02x}")
print(f"  ct_hex: {ct_a.hex()}")

# Vector B: Init Request with corrected flag 0x03C0
p_b = b'{"action": "INIT_CHANNEL", "session_id": "sess_01"}'
raw_b = bytearray(struct.pack("<H", 0x03C0)) + p_b + struct.pack("<I", 1) + struct.pack("<I", 1) + b"\x00\x00\x00\x00"
csum_b = calc_csum(bytes(raw_b), len(raw_b)-4)
struct.pack_into("<I", raw_b, len(raw_b)-4, csum_b)
pad_b = 8 - (len(raw_b) % 8)
padded_b = bytes(raw_b) + bytes(pad_b - 1) + bytes([pad_b])
ct_b = pbc_encrypt(KEY, padded_b)
print("\nVECTOR B (Init 0x03C0):")
print(f"  raw_len: {len(raw_b)}")
print(f"  csum: 0x{csum_b:08x}")
print(f"  padded_len: {len(padded_b)}")
print(f"  pad_trailer: 0x{padded_b[-1]:02x}")
print(f"  ct_hex: {ct_b.hex()}")

# Vector C: App Message with corrected flag 0x01C8
p_c = b"PING_MESSAGE_ON_CHANNEL_1"
raw_c = bytearray(struct.pack("<H", 0x01C8)) + p_c + struct.pack("<I", 2) + struct.pack("<I", 1) + b"\x00\x00\x00\x00"
csum_c = calc_csum(bytes(raw_c), len(raw_c)-4)
struct.pack_into("<I", raw_c, len(raw_c)-4, csum_c)
pad_c = 8 - (len(raw_c) % 8)
padded_c = bytes(raw_c) + bytes(pad_c - 1) + bytes([pad_c])
ct_c = pbc_encrypt(KEY, padded_c)
print("\nVECTOR C (App Message 0x01C8):")
print(f"  raw_len: {len(raw_c)}")
print(f"  csum: 0x{csum_c:08x}")
print(f"  padded_len: {len(padded_c)}")
print(f"  pad_trailer: 0x{padded_c[-1]:02x}")
print(f"  ct_hex: {ct_c.hex()}")

# Vector D: App Response with corrected flag 0x01CC (with 1 ACK)
# Footers forward order: SeqNum (4B), ChannelID (4B), ACKs (1*4B + 1B = 5B), Checksum (4B)
# Note: In reverse order from tail: Checksum -> ChannelID -> ACKs -> SeqNum.
# Wait, let's verify reverse order layout for pack():
# In packet_parser.pack:
# If with_checksum: tail has checksum (4B)
# Next from tail is piggyback (if any)
# Next from tail is channel_id (if any, 4B)
# Next from tail is acks (if any, N*4B + 1B)
# Next from tail is seq_num (if any, 4B)
# Next from tail is fragments (if any, 8B)
# Next from tail is first_request_offset (if any, 2B)
# Therefore, in forward order:
# [ReqOffset] [Fragments] [SeqNum] [ACKs] [ChannelID] [Piggyback] [Checksum]
p_d = b"ACK_AND_ECHO:PING_MESSAGE_ON_CHANNEL_1"
raw_d = bytearray(struct.pack("<H", 0x01CC)) + p_d
# forward order of footers:
raw_d.extend(struct.pack("<I", 1001)) # seq_num
raw_d.extend(struct.pack("<I", 2))    # ack seq 2
raw_d.append(1)                       # ack count 1
raw_d.extend(struct.pack("<I", 1))    # channel_id
raw_d.extend(b"\x00\x00\x00\x00")     # checksum placeholder
csum_d = calc_csum(bytes(raw_d), len(raw_d)-4)
struct.pack_into("<I", raw_d, len(raw_d)-4, csum_d)
pad_d = 8 - (len(raw_d) % 8)
padded_d = bytes(raw_d) + bytes(pad_d - 1) + bytes([pad_d])
ct_d = pbc_encrypt(KEY, padded_d)
print("\nVECTOR D (App Response 0x01CC):")
print(f"  raw_len: {len(raw_d)}")
print(f"  csum: 0x{csum_d:08x}")
print(f"  padded_len: {len(padded_d)}")
print(f"  pad_trailer: 0x{padded_d[-1]:02x}")
print(f"  ct_hex: {ct_d.hex()}")
