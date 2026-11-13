"""
Integration tests for Mercury UDP Transport Server and Channels.
Validates:
1. UDP socket listener startup and shutdown.
2. Live UDP packet transmission and receipt on localhost.
3. Sliding window sequence number assignment and tracking.
4. Window overflow protection (sendWindUsage > 256).
5. Safe rejection of malformed / corrupted datagrams without socket interruption.
6. Acknowledgment generation and processing.
"""

import asyncio
import socket
import pytest

from mercury.constants import FLAG_RELIABLE, MAX_WINDOW_SIZE
from mercury.channel import ChannelOverflowError, MercuryChannel
from mercury.packet import MercuryPacket
from mercury.transport import MercuryTransportServer


class TestMercuryChannelLogic:
    """Unit tests for MercuryChannel sliding window and ACK handling."""

    def test_sequence_number_progression(self):
        channel = MercuryChannel(("127.0.0.1", 20001))
        p0 = channel.create_packet(body=b"Packet0", reliable=True)
        p1 = channel.create_packet(body=b"Packet1", reliable=True)
        p2 = channel.create_packet(body=b"Packet2", reliable=True)

        assert p0.seq_num == 0
        assert p1.seq_num == 1
        assert p2.seq_num == 2
        assert channel.send_wind_usage == 3
        assert channel.large_out_seq_at == 3
        assert channel.oldest_unacked_seq == 0

    def test_ack_processing_advances_window(self):
        channel = MercuryChannel(("127.0.0.1", 20001))
        p0 = channel.create_packet(body=b"Packet0", reliable=True)
        p1 = channel.create_packet(body=b"Packet1", reliable=True)
        p2 = channel.create_packet(body=b"Packet2", reliable=True)

        # Remote acknowledges packet 0 and 1
        channel.process_acks([0, 1])
        assert channel.oldest_unacked_seq == 2
        assert channel.send_wind_usage == 1
        assert 0 not in channel.unacked_packets
        assert 1 not in channel.unacked_packets
        assert 2 in channel.unacked_packets

    def test_window_overflow_guard(self):
        channel = MercuryChannel(("127.0.0.1", 20001))
        # Fill the window up to MAX_WINDOW_SIZE (256)
        for i in range(MAX_WINDOW_SIZE):
            channel.create_packet(body=b"Data", reliable=True)

        assert channel.send_wind_usage == MAX_WINDOW_SIZE

        # The 257th unacknowledged reliable packet must raise ChannelOverflowError
        with pytest.raises(ChannelOverflowError, match="channel has overflowed"):
            channel.create_packet(body=b"OverflowData", reliable=True)

    def test_duplicate_incoming_packet_detection(self):
        channel = MercuryChannel(("127.0.0.1", 20001))
        packet = MercuryPacket(flags=FLAG_RELIABLE, seq_num=5, body=b"Hello")

        # First receive
        is_dup, msgs = channel.receive_packet(packet)
        assert is_dup is False
        assert 5 in channel.received_seqs

        # Second receive with same seq_num is marked duplicate
        is_dup2, msgs2 = channel.receive_packet(packet)
        assert is_dup2 is True
        assert msgs2 == []


class TestMercuryTransportServer:
    """Integration tests running real async UDP sockets on localhost."""

    @pytest.mark.asyncio
    async def test_udp_listener_startup_and_shutdown(self):
        server = MercuryTransportServer(host="127.0.0.1", port=21050)
        assert not server.is_running
        await server.start()
        assert server.is_running
        assert server.transport is not None

        # Clean shutdown
        await server.stop()
        assert not server.is_running
        assert server.transport is None

    @pytest.mark.asyncio
    async def test_receive_and_acknowledge_reliable_datagram(self):
        received_events = []

        def handle_packet(addr, channel, packet, messages):
            received_events.append((addr, packet))

        server = MercuryTransportServer(host="127.0.0.1", port=21051, on_packet_received=handle_packet)
        await server.start()

        client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_sock.settimeout(1.0)

        try:
            # Client sends a reliable packet with sequence number 0
            client_packet = MercuryPacket(
                flags=FLAG_RELIABLE,
                seq_num=0,
                body=b"ClientPing"
            )
            raw = client_packet.encode()
            client_sock.sendto(raw, ("127.0.0.1", 21051))

            # Allow event loop to process incoming datagram and respond with ACK
            await asyncio.sleep(0.05)

            # Server will process it and send back an ACK packet
            ack_raw, _ = client_sock.recvfrom(2048)
            ack_packet = MercuryPacket.decode(ack_raw)

            # Assert ACK was received
            assert len(ack_packet.acks) == 1
            assert ack_packet.acks[0] == 0

            # Wait briefly for server callback to process
            await asyncio.sleep(0.05)
            assert len(received_events) == 1
            assert received_events[0][1].body == b"ClientPing"
            assert server.stats["packets_received"] >= 1
            assert server.stats["packets_sent"] >= 1
        finally:
            client_sock.close()
            await server.stop()

    @pytest.mark.asyncio
    async def test_malformed_packet_rejection_over_socket(self):
        server = MercuryTransportServer(host="127.0.0.1", port=21052)
        await server.start()

        client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_sock.settimeout(0.5)

        try:
            # Send garbage / undersized bytes
            client_sock.sendto(b"\x00\x00", ("127.0.0.1", 21052))
            client_sock.sendto(b"\xFF\xFF\x00\x00\x00", ("127.0.0.1", 21052))

            await asyncio.sleep(0.05)

            # Server must still be running and stats should record rejected packets
            assert server.is_running
            assert server.stats["malformed_packets_rejected"] == 2

            # Now send a valid packet to prove socket is intact
            valid_packet = MercuryPacket(body=b"ValidAfterGarbage")
            client_sock.sendto(valid_packet.encode(), ("127.0.0.1", 21052))

            await asyncio.sleep(0.05)
            assert server.stats["packets_received"] == 3
        finally:
            client_sock.close()
            await server.stop()
