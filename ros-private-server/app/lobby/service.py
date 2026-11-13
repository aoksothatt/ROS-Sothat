import time
from typing import Dict, List, Optional
from fastapi import HTTPException, status
from app.config import settings
from app.lobby.models import PlayerPresence, PresenceStatus
from app.lobby.schemas import PlayerPresenceOut

class LobbyService:
    _instance: Optional["LobbyService"] = None

    @classmethod
    def get_instance(cls) -> "LobbyService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        # Maps GID -> PlayerPresence
        self._presences: Dict[int, PlayerPresence] = {}

    def cleanup_stale_presences(self) -> List[int]:
        from app.room.service import RoomService
        from app.matchmaking.service import MatchmakingService

        now = time.time()
        timeout = settings.LOBBY_HEARTBEAT_TIMEOUT_SECONDS
        stale_gids = [
            gid for gid, p in list(self._presences.items())
            if (now - p.last_heartbeat) > timeout
        ]
        room_service = RoomService.get_instance()
        mm_service = MatchmakingService.get_instance()

        for gid in stale_gids:
            if gid in self._presences:
                del self._presences[gid]
            # Safely cascade disconnect to active rooms and matchmaking queues
            try:
                room_service.handle_player_disconnect(gid)
            except Exception:
                pass
            try:
                mm_service.handle_player_disconnect(gid)
            except Exception:
                pass

        return stale_gids

    def enter_lobby(self, account_id: int, gid: int, nickname: str, level: int) -> PlayerPresence:
        self.cleanup_stale_presences()
        presence = PlayerPresence(
            gid=gid,
            account_id=account_id,
            nickname=nickname,
            level=level,
            status=PresenceStatus.IDLE,
            last_heartbeat=time.time()
        )
        self._presences[gid] = presence
        return presence

    def heartbeat(self, gid: int) -> PlayerPresence:
        presence = self._presences.get(gid)
        if not presence:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Player is not registered in the active lobby. Please call /enter first."
            )
        presence.last_heartbeat = time.time()
        return presence

    def leave_lobby(self, gid: int) -> bool:
        if gid in self._presences:
            del self._presences[gid]
            return True
        return False

    def get_presence(self, gid: int) -> Optional[PlayerPresence]:
        return self._presences.get(gid)

    def set_presence_status(
        self,
        gid: int,
        new_status: PresenceStatus,
        room_id: Optional[str] = None,
        match_id: Optional[str] = None
    ) -> None:
        presence = self._presences.get(gid)
        if presence:
            presence.status = new_status
            presence.room_id = room_id
            presence.match_id = match_id
            presence.last_heartbeat = time.time()

    def list_online_players(self) -> List[PlayerPresenceOut]:
        self.cleanup_stale_presences()
        now = time.time()
        result = []
        for p in self._presences.values():
            result.append(PlayerPresenceOut(
                gid=p.gid,
                nickname=p.nickname,
                level=p.level,
                status=p.status,
                room_id=p.room_id,
                last_heartbeat_seconds_ago=round(now - p.last_heartbeat, 1)
            ))
        return result

def get_lobby_service() -> LobbyService:
    return LobbyService.get_instance()
