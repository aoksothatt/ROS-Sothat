"""
Mercury reliable UDP protocol constants.
Directly recovered from client binary disassembly (Mach-O ARM64 neox::bwclient::Mercury).
"""

# Packet Flag Bits (16-bit bitmask, flags < 0x0400)
FLAG_RELIABLE: int = 0x0001              # Delivery must be acknowledged
FLAG_HAS_PIGGYBACKS: int = 0x0002        # Datagram contains piggybacked sub-packets
FLAG_HAS_ACKS: int = 0x0004              # Datagram contains an ACK footer
FLAG_ONCE_OFF: int = 0x0008              # Standalone once-off datagram
FLAG_HAS_REQUESTS: int = 0x0010          # Contains request offsets for RPC replies
FLAG_IS_FRAGMENT: int = 0x0020           # Packet is part of a fragmented bundle
FLAG_HAS_SEQUENCE_NUMBER: int = 0x0040   # Contains a 32-bit sequence number footer
FLAG_INDEXED_CHANNEL: int = 0x0080       # Packet contains an indexed channel ID footer
FLAG_HAS_CHECKSUM: int = 0x0100          # Packet contains a 32-bit checksum footer
FLAG_CREATE_CHANNEL: int = 0x0200        # Channel creation handshake request

# Protocol Bounds
MAX_VALID_FLAGS: int = 0x03FF            # Any flags >= 0x0400 triggers bad flags error
MIN_PACKET_SIZE: int = 3                 # Must be > 2 bytes (flags + payload/footer)
DEFAULT_MTU: int = 1472                  # Standard maximum UDP payload for Ethernet
MAX_WINDOW_SIZE: int = 256               # Sliding window overflow limit before disconnect

# Mercury Error / Reason Codes
REASON_SUCCESS: int = 0
REASON_CORRUPTED_PACKET: int = -1
REASON_NONEXISTENT_CHANNEL: int = -2
REASON_WINDOW_OVERFLOW: int = -3
REASON_GENERAL_NETWORK: int = -4

# InterfaceElement Message Length Encoding
LENGTH_FIXED: int = 0                    # Fixed payload size (no length prefix in body)
LENGTH_VARIABLE_1: int = 1               # 1-byte length prefix (0 - 254 bytes)
LENGTH_VARIABLE_2: int = 2               # 2-byte length prefix (0 - 65535 bytes)
LENGTH_VARIABLE_4: int = 4               # 4-byte length prefix
