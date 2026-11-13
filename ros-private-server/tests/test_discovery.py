"""
Unit and integration tests for Server Discovery service.
Validates:
1. Exact server_list_ios.txt format.
2. Configurable IP and port.
3. Client-side parser compatibility.
4. Error handling on invalid configurations.
5. FastAPI HTTP endpoint responses.
"""

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from discovery.config import ServerEntry, DiscoverySettings
from discovery.parser import parse_sa_server_info, parse_sa_server_list
from discovery.service import DiscoveryService


class TestDiscoveryParser:
    """Tests for the recovered client-side parser."""

    def test_parse_valid_single_entry(self):
        line = "1 1 0 1 ROS_Sothat Sothat 192.168.1.100 192.168.1.100 192.168.1.100 1001 192.168.1.100:20001:20002"
        info = parse_sa_server_info(line)
        assert info is not None
        assert info['zone'] == 1
        assert info['numberSt'] == 1
        assert info['net'] == 0
        assert info['serverSt'] == 1
        assert info['name'] == "ROS_Sothat"
        assert info['oriName'] == "Sothat"
        assert info['tel'] == "192.168.1.100"
        assert info['cnc'] == "192.168.1.100"
        assert info['edu'] == "192.168.1.100"
        assert info['hostID'] == 1001
        assert info['isLoginServer'] == 1
        assert info['loginIP'] == "192.168.1.100"
        assert info['loginPort'] == 20001
        assert info['battlePort'] == 20002

    def test_parse_valid_without_battle_port(self):
        line = "2 5 1 2 EU_Cluster EU 10.0.0.1 10.0.0.1 10.0.0.1 2001 10.0.0.1:20001"
        info = parse_sa_server_info(line)
        assert info is not None
        assert info['zone'] == 2
        assert info['numberSt'] == 5
        assert info['net'] == 1
        assert info['serverSt'] == 2
        assert info['name'] == "EU_Cluster"
        assert info['loginIP'] == "10.0.0.1"
        assert info['loginPort'] == 20001
        assert info['battlePort'] == 0

    def test_parse_comments_and_empty_lines(self):
        assert parse_sa_server_info("") is None
        assert parse_sa_server_info("   ") is None
        assert parse_sa_server_info("# Network configuration header") is None
        assert parse_sa_server_info("#network comment") is None

    def test_parse_invalid_field_count(self):
        # Only 10 fields (missing login endpoint)
        line = "1 1 0 1 Sothat Sothat 127.0.0.1 127.0.0.1 127.0.0.1 1001"
        assert parse_sa_server_info(line) is None

        # 12 fields (extra field)
        line = "1 1 0 1 Sothat Sothat 127.0.0.1 127.0.0.1 127.0.0.1 1001 127.0.0.1:20001:20002 EXTRA"
        assert parse_sa_server_info(line) is None

    def test_parse_corrupted_numerical_values(self):
        line = "NOT_A_ZONE 1 0 1 Sothat Sothat 127.0.0.1 127.0.0.1 127.0.0.1 1001 127.0.0.1:20001:20002"
        assert parse_sa_server_info(line) is None

        line = "1 1 0 1 Sothat Sothat 127.0.0.1 127.0.0.1 127.0.0.1 1001 127.0.0.1:BAD_PORT"
        assert parse_sa_server_info(line) is None


class TestDiscoveryService:
    """Tests for ServerEntry and DiscoveryService logic."""

    def setup_method(self):
        DiscoveryService.reset_instance()

    def test_server_entry_validation_valid(self):
        entry = ServerEntry(
            zone=1,
            number_st=1,
            net_st=0,
            server_st=1,
            name="MyServer",
            ori_name="LocalCluster",
            tel_ip="127.0.0.1",
            cnc_ip="127.0.0.1",
            edu_ip="127.0.0.1",
            host_id=1001,
            login_ip="127.0.0.1",
            login_port=20001,
            battle_port=20002
        )
        entry.validate()
        line = entry.to_line()
        assert len(line.split(' ')) == 11

    def test_server_entry_validation_invalid_ports(self):
        with pytest.raises(ValueError, match="login_port"):
            ServerEntry(login_port=0).validate()

        with pytest.raises(ValueError, match="login_port"):
            ServerEntry(login_port=70000).validate()

        with pytest.raises(ValueError, match="battle_port"):
            ServerEntry(battle_port=-1).validate()

    def test_server_entry_validation_invalid_names(self):
        with pytest.raises(ValueError, match="name must be non-empty and cannot contain spaces"):
            ServerEntry(name="Name With Spaces").validate()

        with pytest.raises(ValueError, match="ori_name must be non-empty and cannot contain spaces"):
            ServerEntry(ori_name="").validate()

    def test_server_entry_validation_invalid_status(self):
        with pytest.raises(ValueError, match="net_st"):
            ServerEntry(net_st=99).validate()

        with pytest.raises(ValueError, match="server_st"):
            ServerEntry(server_st=5).validate()

        with pytest.raises(ValueError, match="zone"):
            ServerEntry(zone=0).validate()

    def test_generate_server_list_content_roundtrip(self):
        service = DiscoveryService.get_instance()
        service.clear_servers()
        s1 = ServerEntry(name="Node1", host_id=1001, login_port=20001)
        s2 = ServerEntry(name="Node2", host_id=1002, login_port=20003)
        service.add_server(s1)
        service.add_server(s2)

        content = service.generate_server_list_content(include_comments=True)
        assert "# Rules of Survival Private Server Discovery" in content
        parsed = parse_sa_server_list(content)
        assert len(parsed) == 2
        assert parsed[0]['name'] == "Node1"
        assert parsed[0]['hostID'] == 1001
        assert parsed[1]['name'] == "Node2"
        assert parsed[1]['hostID'] == 1002


class TestDiscoveryEndpoints:
    """Integration tests for FastAPI discovery routes."""

    @pytest.mark.asyncio
    async def test_server_list_ios_endpoint(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/server_list_ios.txt")
            assert resp.status_code == 200
            assert "text/plain" in resp.headers["content-type"]
            content = resp.text
            parsed = parse_sa_server_list(content)
            assert len(parsed) >= 1
            entry = parsed[0]
            assert entry['isLoginServer'] == 1
            assert entry['loginPort'] > 0

    @pytest.mark.asyncio
    async def test_server_list_all_endpoint(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/server_list_all.txt")
            assert resp.status_code == 200
            assert "text/plain" in resp.headers["content-type"]
            parsed = parse_sa_server_list(resp.text)
            assert len(parsed) >= 1

    @pytest.mark.asyncio
    async def test_system_notice_endpoint(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/notice_ios_hw.txt")
            assert resp.status_code == 200
            assert "ROS Sothat Private Server" in resp.text

    @pytest.mark.asyncio
    async def test_discovery_servers_json_endpoint(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/discovery/servers")
            assert resp.status_code == 200
            data = resp.json()
            assert "count" in data
            assert "servers" in data
            assert data["count"] >= 1
