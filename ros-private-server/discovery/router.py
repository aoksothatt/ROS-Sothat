"""
FastAPI router serving ROS Legacy server discovery files.
Endpoints mirror the documented client requests:
- GET /server_list_ios.txt
- GET /server_list_all.txt
- GET /notice_ios_hw.txt
"""

from fastapi import APIRouter, Response, status
from fastapi.responses import PlainTextResponse
from discovery.service import DiscoveryService

router = APIRouter(tags=["Discovery"])


@router.get(
    "/server_list_ios.txt",
    response_class=PlainTextResponse,
    summary="Get iOS Server Discovery List",
    description="Returns the exact plaintext server_list_ios.txt format consumed by the original ROS Legacy iOS client."
)
async def get_server_list_ios():
    service = DiscoveryService.get_instance()
    content = service.generate_server_list_content()
    return PlainTextResponse(content=content, media_type="text/plain")


@router.get(
    "/server_list_all.txt",
    response_class=PlainTextResponse,
    summary="Get All Platforms Server Discovery List",
    description="Returns the server list format for all platforms."
)
async def get_server_list_all():
    service = DiscoveryService.get_instance()
    content = service.generate_server_list_content()
    return PlainTextResponse(content=content, media_type="text/plain")


@router.get(
    "/notice_ios_hw.txt",
    response_class=PlainTextResponse,
    summary="Get System Maintenance / Notice",
    description="Returns the system notice requested by extconfigs.py."
)
async def get_system_notice():
    notice = "ROS Sothat Private Server - Ready for local iOS research."
    return PlainTextResponse(content=notice, media_type="text/plain")


@router.get(
    "/api/v1/discovery/servers",
    summary="List Registered Discovery Servers (JSON)",
    description="Structured JSON representation for administration and debugging."
)
async def list_servers_json():
    service = DiscoveryService.get_instance()
    servers = service.get_servers()
    return {
        "count": len(servers),
        "servers": [
            {
                "zone": s.zone,
                "number_st": s.number_st,
                "net_st": s.net_st,
                "server_st": s.server_st,
                "name": s.name,
                "ori_name": s.ori_name,
                "tel_ip": s.tel_ip,
                "cnc_ip": s.cnc_ip,
                "edu_ip": s.edu_ip,
                "host_id": s.host_id,
                "login_ip": s.login_ip,
                "login_port": s.login_port,
                "battle_port": s.battle_port
            }
            for s in servers
        ]
    }
