# ROS Legacy — Mercury UDP & Server Discovery Protocol Specification

**Document Version**: 1.0 (Phase 6.1 Prototype)  
**Target Platform**: iOS Only (`RoS-Legacy-iOS.ipa`)  
**Network Heritage**: NetEase NeoX Engine embedding BigWorld Technology `bwclient` (`neox::bwclient::Mercury`).

---

## 1. Server Discovery Format (`server_list_ios.txt`)

The iOS client discovers clusters over HTTPS from port `50010` (`ExtConfigs::getServiceAccessPoint`).

### Line Format
```text
<zone> <numberSt> <netSt> <serverSt> <name> <oriName> <telIP> <cncIP> <eduIP> <hostID> <loginIP>:<loginPort>:<battlePort>
```

### Field Definitions
| Index | Field | Type | Description |
|---|---|---|---|
| 0 | `zone` | `int` | Category / region identifier (1 = NA, 2 = EU, etc.) |
| 1 | `numberSt` | `int` | Display order index |
| 2 | `netSt` | `int` | Network condition (0 = Normal, 1 = Busy) |
| 3 | `serverSt` | `int` | Operational status (1 = Online/Smooth, 2 = Crowded, 3 = Maintenance) |
| 4 | `name` | `str` | Display name (cannot contain spaces) |
| 5 | `oriName` | `str` | Cluster internal identifier (cannot contain spaces) |
| 6 | `telIP` | `str` | Telecom ISP fallback address |
| 7 | `cncIP` | `str` | Unicom ISP fallback address |
| 8 | `eduIP` | `str` | Education network ISP fallback address |
| 9 | `hostID` | `int` | Unique cluster identifier |
| 10 | `endpoint` | `str` | Target endpoints formatted as `<loginIP>:<loginPort>:<battlePort>` |

---

## 2. Mercury UDP Transport Wire Format

### 2.1 Packet Layout
```
+-------------------------------------------------------------+
| Header: Flags (uint16_t, Little-Endian)                     |
+-------------------------------------------------------------+
| Body: Message 1, Message 2, ...                             |
+-------------------------------------------------------------+
| [Optional] Fragment footer                                  |
| [Optional] Request offset footer                            |
| [Optional] Sequence number footer (uint32_t)                |
| [Optional] ACKs footer (uint32_t acks[count] + uint8_t count)
| [Optional] Indexed channel ID footer (uint32_t)             |
| [Optional] Piggyback footer                                 |
| [Optional] Checksum footer (uint32_t CRC32)                 |
+-------------------------------------------------------------+
```

### 2.2 Packet Flags
| Flag Constant | Bitmask | Description |
|---|---|---|
| `FLAG_RELIABLE` | `0x0001` | Reliable delivery requested |
| `FLAG_HAS_PIGGYBACKS` | `0x0002` | Datagram contains piggybacked sub-packets |
| `FLAG_HAS_ACKS` | `0x0004` | Datagram contains an ACK footer |
| `FLAG_ONCE_OFF` | `0x0008` | Standalone once-off datagram |
| `FLAG_HAS_REQUESTS` | `0x0010` | Contains request offsets for RPC replies |
| `FLAG_IS_FRAGMENT` | `0x0020` | Part of a fragmented bundle |
| `FLAG_HAS_SEQUENCE_NUMBER` | `0x0040` | Contains a 32-bit sequence number footer |
| `FLAG_INDEXED_CHANNEL` | `0x0080` | Contains an indexed channel ID footer |
| `FLAG_HAS_CHECKSUM` | `0x0100` | Contains a 32-bit checksum footer |
| `FLAG_CREATE_CHANNEL` | `0x0200` | Channel creation handshake request |
| `MAX_VALID_FLAGS` | `0x03FF` | Bitmask boundary (flags $\ge$ `0x0400` are rejected) |

---

## 3. Sliding Window & Reliability Invariants

1. **Window Overflow Limit**:
   The sliding window usage is defined as:
   $$\text{sendWindUsage} = \text{largeOutSeqAt} - \text{oldestUnackedSeq}$$
   If unacknowledged packets exceed `MAX_WINDOW_SIZE` (256 packets), the channel forcibly disconnects with:
   `"ServerConnection::send: Disconnecting since channel has overflowed largeOutSeqAt %d, oldestUnackedSeq %d, sendWindUsage %d"`
2. **Cumulative & Selective ACKs**:
   Packets carry an ACK array up to 255 items. When received, the transmitter retires acknowledged packets and advances `oldestUnackedSeq`.
3. **Safe Datagram Rejection**:
   Undersized datagrams ($< 3$ bytes), bad flags ($\ge 0x0400$), checksum mismatches, zero-count ACK footers, and truncated footer lengths are rejected without crashing the listener.
