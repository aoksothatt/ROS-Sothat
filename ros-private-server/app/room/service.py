import secrets
import hashlib
import hmac
import time
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import HTTPException, status
from app.config import settings
from app.lobby.service import LobbyService, PresenceStatus
from app.room.models import Room, RoomMember, RoomStatus
from app.room.schemas import RoomCreateRequest, RoomOut, RoomMemberOut, RoomStartResponse

class RoomService:
    _instance: Optional["RoomService"] = None

    @classmethod
    def get_instance(cls) -> "RoomService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        # Maps room_id -> Room
        self._rooms: Dict[str, Room] = {}

    @staticmethod
    def _hash_password(raw_pwd: Optional[str]) -> Optional[str]:
        if not raw_pwd:
            return None
        return hashlib.sha256(raw_pwd.encode("utf-8")).hexdigest()

    def create_room(self, host_gid: int, host_nickname: str, host_level: int, req: RoomCreateRequest) -> RoomOut:
        lobby_service = LobbyService.get_instance()
        
        # Check if host is already in another room
        for r in self._rooms.values():
            if host_gid in r.members:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"You are already in room '{r.name}' ({r.room_id}). Leave it first."
                )

        room_id = f"room_{secrets.token_hex(4)}"
        pwd_hash = self._hash_password(req.password)
        
        host_member = RoomMember(
            gid=host_gid,
            nickname=host_nickname,
            level=host_level,
            is_host=True,
            is_ready=True,
            slot_idx=0
        )
        
        room = Room(
            room_id=room_id,
            name=req.name.strip(),
            host_gid=host_gid,
            map_id=req.map_id,
            capacity=req.capacity,
            team_mode=req.team_mode,
            is_public=req.is_public,
            password_hash=pwd_hash,
            status=RoomStatus.WAITING,
            members={host_gid: host_member}
        )
        self._rooms[room_id] = room
        lobby_service.set_presence_status(host_gid, PresenceStatus.IN_ROOM, room_id=room_id)
        
        return self._to_room_out(room)

    def join_room(self, room_id: str, gid: int, nickname: str, level: int, password: Optional[str] = None) -> RoomOut:
        lobby_service = LobbyService.get_instance()
        room = self._rooms.get(room_id)
        if not room or room.status == RoomStatus.CLOSED:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found.")

        if room.status == RoomStatus.PLAYING:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Match is already in progress.")

        if len(room.members) >= room.capacity:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Room is full.")

        if gid in room.members:
            return self._to_room_out(room)

        # Check if user is already a member of another room
        for r in self._rooms.values():
            if r.room_id != room_id and gid in r.members:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"You are already in room '{r.name}' ({r.room_id}). Leave it first."
                )

        # Check password if set (using constant-time comparison)
        if room.password_hash:
            computed_pwd = self._hash_password(password)
            if not password or not computed_pwd or not hmac.compare_digest(computed_pwd, room.password_hash):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Incorrect room password.")

        # Determine next available slot index
        used_slots = {m.slot_idx for m in room.members.values()}
        slot = 0
        while slot in used_slots:
            slot += 1

        member = RoomMember(
            gid=gid,
            nickname=nickname,
            level=level,
            is_host=False,
            is_ready=False,
            slot_idx=slot
        )
        room.members[gid] = member
        lobby_service.set_presence_status(gid, PresenceStatus.IN_ROOM, room_id=room_id)
        return self._to_room_out(room)

    def leave_room(self, room_id: str, gid: int) -> dict:
        lobby_service = LobbyService.get_instance()
        room = self._rooms.get(room_id)
        if not room or gid not in room.members:
            return {"message": "Not in room."}

        was_host = room.members[gid].is_host
        del room.members[gid]
        lobby_service.set_presence_status(gid, PresenceStatus.IDLE, room_id=None)

        if not room.members:
            # Room is empty, destroy it
            room.status = RoomStatus.CLOSED
            del self._rooms[room_id]
            return {"message": "Left room; room closed because it is now empty."}

        # If host left, migrate host role to the oldest remaining member
        if was_host:
            next_host_gid = next(iter(room.members.keys()))
            room.members[next_host_gid].is_host = True
            room.members[next_host_gid].is_ready = True
            room.host_gid = next_host_gid

        return {"message": "Successfully left room."}

    def handle_player_disconnect(self, gid: int) -> None:
        """Called when a player disconnects or times out to clean up room membership safely."""
        target_rooms = [r.room_id for r in list(self._rooms.values()) if gid in r.members]
        for rid in target_rooms:
            self.leave_room(rid, gid)

    def cleanup_stale_rooms(self, max_idle_seconds: Optional[int] = None) -> int:
        """Purges closed, empty, or expired rooms from memory."""
        if max_idle_seconds is None:
            max_idle_seconds = settings.ROOM_IDLE_TIMEOUT_SECONDS

        now_utc = datetime.utcnow()
        pruned_count = 0
        stale_room_ids = []

        for room_id, room in list(self._rooms.items()):
            age = (now_utc - room.created_at).total_seconds()
            if room.status == RoomStatus.CLOSED or len(room.members) == 0:
                stale_room_ids.append(room_id)
            elif age > max_idle_seconds and room.status != RoomStatus.PLAYING:
                stale_room_ids.append(room_id)

        for rid in stale_room_ids:
            if rid in self._rooms:
                del self._rooms[rid]
                pruned_count += 1

        return pruned_count

    def set_ready(self, room_id: str, gid: int, is_ready: bool) -> RoomOut:
        room = self._rooms.get(room_id)
        if not room or gid not in room.members:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not in room.")

        member = room.members[gid]
        if member.is_host:
            # Host is always ready
            member.is_ready = True
        else:
            member.is_ready = is_ready

        # Update room status if all members ready
        all_ready = all(m.is_ready for m in room.members.values())
        if all_ready and len(room.members) > 0:
            room.status = RoomStatus.READY
        else:
            room.status = RoomStatus.WAITING

        return self._to_room_out(room)

    def kick_member(self, room_id: str, host_gid: int, target_gid: int) -> RoomOut:
        lobby_service = LobbyService.get_instance()
        room = self._rooms.get(room_id)
        if not room or room.host_gid != host_gid:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only room host can kick members.")

        if target_gid == host_gid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Host cannot kick themselves.")

        if target_gid not in room.members:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target player not in room.")

        del room.members[target_gid]
        lobby_service.set_presence_status(target_gid, PresenceStatus.IDLE, room_id=None)
        return self._to_room_out(room)

    def start_room_match(self, room_id: str, host_gid: int) -> RoomStartResponse:
        lobby_service = LobbyService.get_instance()
        room = self._rooms.get(room_id)
        if not room or room.host_gid != host_gid:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only host can start the match.")

        # Check readiness
        unready = [m.nickname for m in room.members.values() if not m.is_ready]
        if unready:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot start match. Unready players: {', '.join(unready)}"
            )

        match_token = f"match_token_{secrets.token_hex(8)}"
        room.status = RoomStatus.PLAYING
        room.match_token = match_token

        # Update presences
        for gid in room.members:
            lobby_service.set_presence_status(gid, PresenceStatus.IN_BATTLE, room_id=room_id, match_id=match_token)

        return RoomStartResponse(
            room_id=room_id,
            status=room.status,
            match_token=match_token,
            battle_server_ip="127.0.0.1",
            battle_server_port=20002,
            player_count=len(room.members)
        )

    def list_rooms(self, is_public_only: bool = True) -> List[RoomOut]:
        result = []
        for r in self._rooms.values():
            if r.status != RoomStatus.CLOSED:
                if is_public_only and not r.is_public:
                    continue
                result.append(self._to_room_out(r))
        return result

    def get_room_details(self, room_id: str) -> RoomOut:
        room = self._rooms.get(room_id)
        if not room or room.status == RoomStatus.CLOSED:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found.")
        return self._to_room_out(room)

    @staticmethod
    def _to_room_out(room: Room) -> RoomOut:
        member_outs = [
            RoomMemberOut(
                gid=m.gid,
                nickname=m.nickname,
                level=m.level,
                is_host=m.is_host,
                is_ready=m.is_ready,
                slot_idx=m.slot_idx
            )
            for m in sorted(room.members.values(), key=lambda x: x.slot_idx)
        ]
        return RoomOut(
            room_id=room.room_id,
            name=room.name,
            host_gid=room.host_gid,
            map_id=room.map_id,
            capacity=room.capacity,
            current_players=len(room.members),
            team_mode=room.team_mode,
            is_public=room.is_public,
            has_password=room.password_hash is not None,
            status=room.status,
            members=member_outs,
            created_at=room.created_at
        )

def get_room_service() -> RoomService:
    return RoomService.get_instance()
