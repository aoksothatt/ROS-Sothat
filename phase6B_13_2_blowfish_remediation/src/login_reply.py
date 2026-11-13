"""
LoginReply Construction and Parsing Specification.

Implements the verified native handshake reply layout:
- BigWorld Reply Header: MsgID 0xFF, 2-byte Length, 4-byte Request ID.
- Status Byte: 0x01 (SUCCESS) or failure code (0x02, 0x03, 0x04, etc.).
- Success Body: 24-byte Blowfish-encrypted BaseApp address block + optional 0x32ef9816 cookie.
- Failure Body: BigWorld variable-length error string.
- Mercury Framing: Header flags and ACKs.
"""

from typing import Optional, Tuple, Union
import struct
import io

from .auth import LoginStatus
from .address import MercuryAddress
from .blowfish_filter import BlowfishAddressFilter
from .bundle_parser import BundleParser, decode_bw_string, encode_bw_string, BIGWORLD_REPLY_MSG_ID
from .mercury_parser import MercuryParser, FLAG_HAS_ACKS, FLAG_HAS_SEQUENCE_NUMBER


SESSION_KEY_MAGIC_COOKIE = 0x32EF9816


class LoginReplyBuilder:
    """Builds and unpacks native-compatible LoginReply datagrams."""

    @classmethod
    def build_success_reply(
        cls,
        request_id: int,
        baseapp_addr: MercuryAddress,
        session_key: bytes,
        replacement_key: Optional[bytes] = None,
        seq_num: Optional[int] = None,
        ack_seq: Optional[int] = None
    ) -> bytes:
        """
        Constructs a complete Mercury datagram containing a successful LoginReply.
        """
        # 1. Prepare and encrypt 24-byte address block
        addr_plain_24 = baseapp_addr.pack_24b()
        addr_encrypted = BlowfishAddressFilter.encrypt(addr_plain_24, session_key)

        # 2. Compose reply body: [Status: 1B] + [Encrypted Address: 24B] + [Optional Cookie & Key]
        body = bytearray()
        body.append(LoginStatus.SUCCESS.value)
        body.extend(addr_encrypted)

        if replacement_key:
            if len(replacement_key) != 56:
                raise ValueError("Replacement session key must be exactly 56 bytes.")
            body.extend(struct.pack('<I', SESSION_KEY_MAGIC_COOKIE))
            body.extend(replacement_key)

        # 3. BigWorld reply bundle: [0xFF] [Length: 2B] [RequestID: 4B] [Body]
        bundle_data = BundleParser.pack_reply(request_id, bytes(body))

        # 4. Mercury transport framing
        acks = [ack_seq] if ack_seq is not None else None
        flags = 0
        if acks:
            flags |= FLAG_HAS_ACKS
        if seq_num is not None:
            flags |= FLAG_HAS_SEQUENCE_NUMBER

        return MercuryParser.pack(
            payload=bundle_data,
            flags=flags,
            seq_num=seq_num,
            acks=acks
        )

    @classmethod
    def build_failure_reply(
        cls,
        request_id: int,
        status: LoginStatus,
        error_message: str,
        seq_num: Optional[int] = None,
        ack_seq: Optional[int] = None
    ) -> bytes:
        """
        Constructs a complete Mercury datagram containing an authentication failure reply.
        """
        # Compose failure body: [Status: 1B] + [Error String: BW string]
        body = bytearray()
        body.append(status.value)
        body.extend(encode_bw_string(error_message))

        # BigWorld reply bundle
        bundle_data = BundleParser.pack_reply(request_id, bytes(body))

        # Mercury framing
        acks = [ack_seq] if ack_seq is not None else None
        flags = 0
        if acks:
            flags |= FLAG_HAS_ACKS
        if seq_num is not None:
            flags |= FLAG_HAS_SEQUENCE_NUMBER

        return MercuryParser.pack(
            payload=bundle_data,
            flags=flags,
            seq_num=seq_num,
            acks=acks
        )

    @classmethod
    def unpack_reply(
        cls,
        datagram: bytes,
        session_key: bytes
    ) -> Tuple[int, LoginStatus, Union[MercuryAddress, str], Optional[bytes]]:
        """
        Unpacks a LoginReply datagram into (request_id, status, address_or_error, replacement_key).
        Used by synthetic clients to verify server responses.
        """
        frame = MercuryParser.unpack(datagram)
        bundle_data = frame.payload

        if len(bundle_data) < 7:
            raise ValueError("Bundle payload too short for BigWorld reply header.")

        msg_id, total_len, request_id = struct.unpack('<BHI', bundle_data[:7])
        if msg_id != BIGWORLD_REPLY_MSG_ID:
            raise ValueError(f"Expected BigWorld reply message ID 0xFF, got 0x{msg_id:02x}.")

        body = bundle_data[7:]
        if not body:
            raise ValueError("Empty reply body.")

        status_byte = body[0]
        status = LoginStatus(status_byte) if status_byte in [s.value for s in LoginStatus] else status_byte

        replacement_key = None

        if status == LoginStatus.SUCCESS:
            if len(body) < 25: # 1B status + 24B encrypted address block
                raise ValueError(f"Success body truncated: expected at least 25 bytes, got {len(body)}.")
            encrypted_addr = body[1:25]
            plain_addr_24 = BlowfishAddressFilter.decrypt(encrypted_addr, session_key)
            address = MercuryAddress.unpack(plain_addr_24)

            # Check for optional replacement session key
            remainder = body[25:]
            if len(remainder) >= 60: # 4B cookie + 56B key
                cookie = struct.unpack('<I', remainder[:4])[0]
                if cookie == SESSION_KEY_MAGIC_COOKIE:
                    replacement_key = remainder[4:60]

            return request_id, status, address, replacement_key
        else:
            # Failure case: read BigWorld error string
            stream = io.BytesIO(body[1:])
            error_msg = decode_bw_string(stream)
            return request_id, status, error_msg, None
