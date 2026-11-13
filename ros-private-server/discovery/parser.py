"""
Recovered client-side parser for ROS server discovery files.
Replicates parseSAServerInfo and parseSAServerList from common/serverlist_utils.py
and parseOneServerInfo from ui/UILogin.py to provide verified round-trip validation.
"""

from typing import Any, Dict, List, Optional


def parse_sa_server_info(line: str) -> Optional[Dict[str, Any]]:
    """
    Parses a single line of server discovery configuration using the exact logic
    recovered from common/serverlist_utils.py (parseSAServerInfo).

    Returns a dictionary of server metadata or None if the line is invalid or a comment.
    """
    line = line.strip()
    if not line or line.startswith('#'):
        return None

    server = line.split(' ')
    # Client strictly verifies len(server) == 11
    if len(server) != 11:
        return None

    try:
        zone = int(server[0])
        number_st = int(server[1])
        net_st = int(server[2])
        server_st = int(server[3])
        name = server[4]
        ori_name = server[5]
        tel_ip = server[6]
        cnc_ip = server[7]
        edu_ip = server[8]
        host_id = int(server[9])

        login_host_id = server[10].split(':')
        login_ip = login_host_id[0]
        login_port = int(login_host_id[1])
        battle_port = int(login_host_id[2]) if len(login_host_id) > 2 else 0
    except (ValueError, IndexError):
        return None

    # Matches the exact dictionary keys created by parseSAServerInfo / parseLocalServerData
    return {
        'zone': zone,
        'numberSt': number_st,
        'serverSt': server_st,
        'name': name,
        'oriName': ori_name,
        'tel': tel_ip,
        'cnc': cnc_ip,
        'edu': edu_ip,
        'net': net_st,
        'hostID': host_id,
        'isLoginServer': 1,
        'loginIP': login_ip,
        'loginPort': login_port,
        'battlePort': battle_port,
    }


def parse_sa_server_list(content: str) -> List[Dict[str, Any]]:
    """
    Parses full discovery file content using the logic from parseSAServerList.
    """
    server_list = []
    lines = content.split('\n')
    for line in lines:
        info = parse_sa_server_info(line)
        if info is not None:
            server_list.append(info)
    return server_list
