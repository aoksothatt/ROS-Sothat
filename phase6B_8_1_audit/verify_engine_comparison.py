"""
Compare independent golden calculation with phase6B_8_local_gateway.protocol_engine
"""
import sys
from pathlib import Path

_PKG_DIR = str(Path(__file__).resolve().parent.parent / "phase6B_8_local_gateway")
_PHASE6B_7_2_DIR = str(Path(__file__).resolve().parent.parent / "phase6B_7_2_synthetic_research")
for d in [_PKG_DIR, _PHASE6B_7_2_DIR]:
    if d not in sys.path:
        sys.path.insert(0, d)

from protocol_engine import MercuryProtocolEngine
from packet_parser import MercuryPacketFlags

KEY = b"ROS_SOTHAT_DETERMINISTIC_SYNTHETIC_BLOWFISH_SESSION_KEY!"
engine = MercuryProtocolEngine(KEY)

# Datagram 1
payload_1 = b'{"action": "INIT_CHANNEL", "session_id": "sess_01"}'
flags_1 = (
    MercuryPacketFlags.FLAG_CREATE_CHANNEL |
    MercuryPacketFlags.FLAG_INDEXED_CHANNEL |
    MercuryPacketFlags.FLAG_HAS_SEQUENCE_NUMBER
)
ct_1 = engine.send_packet(
    payload=payload_1,
    flags=flags_1,
    seq_num=1,
    channel_id=1,
    enable_checksum=True
)
print("Engine Datagram 1 Ciphertext Hex:")
print(ct_1.hex())

# Datagram 2
payload_2 = b"PING_MESSAGE_ON_CHANNEL_1"
flags_2 = (
    MercuryPacketFlags.FLAG_ON_CHANNEL |
    MercuryPacketFlags.FLAG_INDEXED_CHANNEL |
    MercuryPacketFlags.FLAG_HAS_SEQUENCE_NUMBER
)
ct_2 = engine.send_packet(
    payload=payload_2,
    flags=flags_2,
    seq_num=2,
    channel_id=1,
    enable_checksum=True
)
print("Engine Datagram 2 Ciphertext Hex:")
print(ct_2.hex())

# Unpack both to test receive pipeline
unpacked_1 = engine.receive_packet(ct_1)
print("\nUnpacked 1 Checksum Valid:", unpacked_1["checksum_verified"])
print("Unpacked 1 Stored Checksum: 0x{:08x}".format(unpacked_1["stored_checksum"]))

unpacked_2 = engine.receive_packet(ct_2)
print("Unpacked 2 Checksum Valid:", unpacked_2["checksum_verified"])
print("Unpacked 2 Stored Checksum: 0x{:08x}".format(unpacked_2["stored_checksum"]))
