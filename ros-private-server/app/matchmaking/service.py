import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import HTTPException, status
from app.config import settings
from app.lobby.service import LobbyService, PresenceStatus
from app.matchmaking.schemas import MatchMode, MatchTicketStatus, MatchStatusResponse, MatchTicketResponse

@dataclass
class MatchTicket:
    ticket_id: str
    gid: int
    nickname: str
    level: int
    match_mode: MatchMode
    region: str
    status: MatchTicketStatus = MatchTicketStatus.QUEUED
    queued_at: datetime = field(default_factory=datetime.utcnow)
    match_id: Optional[str] = None
    match_token: Optional[str] = None
    battle_server_ip: Optional[str] = None
    battle_server_port: Optional[int] = None
    assigned_players: List[str] = field(default_factory=list)

class MatchmakingService:
    _instance: Optional["MatchmakingService"] = None

    @classmethod
    def get_instance(cls) -> "MatchmakingService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        # Maps ticket_id -> MatchTicket
        self._tickets: Dict[str, MatchTicket] = {}
        # Maps gid -> ticket_id
        self._player_tickets: Dict[int, str] = {}

    def enqueue(self, gid: int, nickname: str, level: int, match_mode: MatchMode, region: str) -> MatchTicketResponse:
        lobby_service = LobbyService.get_instance()
        
        # Check if player already queued
        if gid in self._player_tickets:
            old_ticket_id = self._player_tickets[gid]
            old_ticket = self._tickets.get(old_ticket_id)
            if old_ticket and old_ticket.status == MatchTicketStatus.QUEUED:
                return MatchTicketResponse(
                    ticket_id=old_ticket.ticket_id,
                    gid=old_ticket.gid,
                    nickname=old_ticket.nickname,
                    match_mode=old_ticket.match_mode,
                    status=old_ticket.status,
                    queued_at=old_ticket.queued_at
                )

        ticket_id = f"ticket_{secrets.token_hex(6)}"
        ticket = MatchTicket(
            ticket_id=ticket_id,
            gid=gid,
            nickname=nickname,
            level=level,
            match_mode=match_mode,
            region=region
        )
        self._tickets[ticket_id] = ticket
        self._player_tickets[gid] = ticket_id
        lobby_service.set_presence_status(gid, PresenceStatus.MATCHMAKING)

        # Trigger matchmaking check
        self.check_and_match(match_mode, region)

        return MatchTicketResponse(
            ticket_id=ticket.ticket_id,
            gid=ticket.gid,
            nickname=ticket.nickname,
            match_mode=ticket.match_mode,
            status=ticket.status,
            queued_at=ticket.queued_at
        )

    def cancel(self, ticket_id: str, gid: int) -> dict:
        lobby_service = LobbyService.get_instance()
        ticket = self._tickets.get(ticket_id)
        if not ticket or ticket.gid != gid:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match ticket not found.")

        if ticket.status == MatchTicketStatus.MATCHED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Match has already been found. Cannot cancel."
            )

        ticket.status = MatchTicketStatus.CANCELLED
        if gid in self._player_tickets:
            del self._player_tickets[gid]
        lobby_service.set_presence_status(gid, PresenceStatus.IDLE)
        return {"message": "Matchmaking ticket cancelled successfully."}

    def handle_player_disconnect(self, gid: int) -> None:
        """Removes a disconnected player from active matchmaking queues."""
        if gid in self._player_tickets:
            ticket_id = self._player_tickets[gid]
            ticket = self._tickets.get(ticket_id)
            if ticket and ticket.status == MatchTicketStatus.QUEUED:
                ticket.status = MatchTicketStatus.TIMEOUT
            del self._player_tickets[gid]

    def cleanup_expired_tickets(
        self,
        ttl_seconds: Optional[int] = None,
        timeout_seconds: Optional[int] = None
    ) -> int:
        """Purges old completed/cancelled tickets and times out inactive queue entries."""
        if ttl_seconds is None:
            ttl_seconds = settings.MATCHMAKING_TICKET_TTL_SECONDS
        if timeout_seconds is None:
            timeout_seconds = settings.MATCHMAKING_TICKET_TIMEOUT_SECONDS

        now_utc = datetime.utcnow()
        to_delete = []

        for ticket_id, ticket in list(self._tickets.items()):
            age = (now_utc - ticket.queued_at).total_seconds()
            # If actively queued but exceeded timeout, transition to TIMEOUT
            if ticket.status == MatchTicketStatus.QUEUED and age > timeout_seconds:
                ticket.status = MatchTicketStatus.TIMEOUT
                if ticket.gid in self._player_tickets:
                    del self._player_tickets[ticket.gid]

            # Prune finalized/expired tickets past TTL
            if ticket.status in (MatchTicketStatus.CANCELLED, MatchTicketStatus.TIMEOUT, MatchTicketStatus.MATCHED):
                if age > ttl_seconds:
                    to_delete.append(ticket_id)

        for tid in to_delete:
            del self._tickets[tid]

        return len(to_delete)

    def get_ticket_status(self, ticket_id: str, gid: int) -> MatchStatusResponse:
        ticket = self._tickets.get(ticket_id)
        if not ticket or ticket.gid != gid:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match ticket not found.")

        return MatchStatusResponse(
            ticket_id=ticket.ticket_id,
            gid=ticket.gid,
            status=ticket.status,
            match_id=ticket.match_id,
            battle_server_ip=ticket.battle_server_ip,
            battle_server_port=ticket.battle_server_port,
            match_token=ticket.match_token,
            assigned_players=ticket.assigned_players if ticket.status == MatchTicketStatus.MATCHED else None
        )

    def check_and_match(self, match_mode: MatchMode, region: str) -> Optional[str]:
        """Matchmaking resolution logic: gathers queued players up to threshold and forms a match."""
        lobby_service = LobbyService.get_instance()
        min_players = settings.MATCHMAKING_MIN_PLAYERS_PER_MATCH

        queued = [
            t for t in self._tickets.values()
            if t.status == MatchTicketStatus.QUEUED
            and t.match_mode == match_mode
            and t.region == region
        ]

        if len(queued) >= min_players:
            # Match formed! Take first N players
            matched_group = queued[:min_players]
            match_id = f"match_{secrets.token_hex(6)}"
            match_token = f"transfer_token_{secrets.token_hex(8)}"
            battle_ip = "127.0.0.1"
            battle_port = 20002
            roster = [t.nickname for t in matched_group]

            for t in matched_group:
                t.status = MatchTicketStatus.MATCHED
                t.match_id = match_id
                t.match_token = match_token
                t.battle_server_ip = battle_ip
                t.battle_server_port = battle_port
                t.assigned_players = roster
                lobby_service.set_presence_status(t.gid, PresenceStatus.IN_BATTLE, match_id=match_id)

            return match_id
        return None

def get_matchmaking_service() -> MatchmakingService:
    return MatchmakingService.get_instance()
