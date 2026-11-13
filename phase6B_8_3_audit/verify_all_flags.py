import capstone

BINARY_PATH = "extracted/Payload/client.app/client"

def get_disasm_slice(start_va, count):
    with open(BINARY_PATH, "rb") as f:
        f.seek(start_va - 0x100000000)
        raw = f.read(count * 4)
    md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
    return [f"0x{ins.address:08x}:  {ins.mnemonic:<8} {ins.op_str}" for ins in md.disasm(raw, start_va)]

flags_evidence = {
    "Bit 0 (0x0001) FLAG_HAS_REQUESTS": [
        (0x100923904, 10, "Receive: Nub::processPacket checks bit 0, unpacks 2-byte request offset"),
        (0x100917254, 8, "Send: Packet assembly sets bit 0 (orr w9, w9, #1) when request offset present"),
        (0x100917ff4, 6, "Send: Footer size calculation checks bit 0, adds 2 to footers length")
    ],
    "Bit 1 (0x0002) FLAG_HAS_PIGGYBACKS": [
        (0x10092297c, 6, "Receive: Nub::processFilteredPacket checks bit 1, branches to piggyback unpacker"),
        (0x1009229fc, 12, "Receive: Piggyback unpacker reads 2-byte length and payload"),
        (0x10092b520, 8, "Send: Sets 0x0102 (FLAG_HAS_CHECKSUM | FLAG_HAS_PIGGYBACKS)")
    ],
    "Bit 2 (0x0004) FLAG_HAS_ACKS": [
        (0x100922994, 6, "Receive: Nub::processFilteredPacket checks bit 2, branches to ACK unpacker"),
        (0x100922e4c, 8, "Receive: Validates remaining length for ACK count footer"),
        (0x100922ee4, 12, "Receive: Unpacks 1-byte count and N*4-byte sequence numbers"),
        (0x100917cf0, 10, "Send: Increments ACK count and sets bit 2 (orr w9, w9, #4)"),
        (0x10091805c, 6, "Send: Footer size calculation checks bit 2, adds 1 to footers length")
    ],
    "Bit 3 (0x0008) FLAG_ON_CHANNEL": [
        (0x1009228a8, 6, "Receive: Checks bit 3 for reliable channel counter"),
        (0x100922984, 6, "Receive: Checks bit 3 to resolve channel by endpoint address"),
        (0x100923120, 6, "Receive: Drops packet if no local channel found for address-based channel")
    ],
    "Bit 4 (0x0010) FLAG_IS_RELIABLE": [
        (0x100922f70, 6, "Receive: Checks bit 4 for reliability requirement"),
        (0x100923090, 10, "Receive: Validates sequence number presence; drops if reliable without seq")
    ],
    "Bit 5 (0x0020) FLAG_HAS_FRAGMENTS": [
        (0x100923948, 6, "Receive: Nub::processPacket checks bit 5, branches to fragment spec unpacker"),
        (0x100923974, 16, "Receive: Unpacks 8-byte fragment footer (fragBegin 4B, fragEnd 4B)"),
        (0x100917ffc, 6, "Send: Footer size calculation checks bit 5, adds 8 to footers length")
    ],
    "Bit 6 (0x0040) FLAG_HAS_SEQUENCE_NUMBER": [
        (0x10092299c, 6, "Receive: Checks bit 6 (tbz w8, #6), branches to sequence number unpacker"),
        (0x100922f50, 8, "Receive: Unpacks 4-byte sequence number into packet->seq_num_"),
        (0x100917fc8, 6, "Send: Sets bit 6 and bit 5 (orr w9, w9, #0x60)"),
        (0x10091804c, 6, "Send: Footer size calculation checks bit 6, adds 4 to footers length")
    ],
    "Bit 7 (0x0080) FLAG_INDEXED_CHANNEL": [
        (0x100922980, 6, "Receive: Checks bit 7, branches to indexed channel unpacker"),
        (0x100922dc0, 14, "Receive: Unpacks 4-byte channel ID into packet->channel_id_"),
        (0x100918008, 6, "Send: Footer size calculation checks bit 7, adds 8 (or 4) to footers length")
    ],
    "Bit 8 (0x0100) FLAG_HAS_CHECKSUM": [
        (0x100922970, 6, "Receive: Checks bit 8, branches to checksum validator"),
        (0x100922a38, 12, "Receive: Unpacks 4-byte checksum from tail, zeroes in-place, computes XOR sum"),
        (0x10092b528, 4, "Send: Sets 0x0100 or 0x0102")
    ],
    "Bit 9 (0x0200) FLAG_CREATE_CHANNEL": [
        (0x1009228b8, 6, "Receive: Checks bit 9 on external nub"),
        (0x100923208, 8, "Receive: Checks bit 9 on channel wanting creation; clears flag and activates channel"),
        (0x100923360, 6, "Receive: Channel activation handler clearing [x22, #0x105]")
    ],
    "Bits 10-15 (0x0400-0x8000) RESERVED / BAD FLAGS": [
        (0x100922898, 4, "Receive: cmp w8, #0x400; b.hs -> Rejects any flags >= 0x0400 with bad flags error")
    ]
}

for flag_name, evidence_list in flags_evidence.items():
    print("=" * 80)
    print(f"FLAG: {flag_name}")
    print("=" * 80)
    for va, count, desc in evidence_list:
        print(f"\n--- {desc} (VA 0x{va:08x}) ---")
        lines = get_disasm_slice(va, count)
        for l in lines:
            print(f"  {l}")
