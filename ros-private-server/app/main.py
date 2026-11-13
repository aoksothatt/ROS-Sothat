import asyncio
import os
from contextlib import asynccontextmanager
from typing import Dict, Any
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.logging_config import setup_logging, get_logger
from app.database.session import init_db
from app.account.router import router as account_router
from app.player.router import router as player_router
from app.lobby.router import router as lobby_router
from app.room.router import router as room_router
from app.matchmaking.router import router as matchmaking_router
from app.admin.router import router as admin_router
from discovery.router import router as discovery_router
from app.lobby.service import LobbyService
from app.room.service import RoomService
from app.matchmaking.service import MatchmakingService

logger = get_logger("main")

def validate_single_worker_configuration(max_allowed: int = settings.MAX_WORKERS_ALLOWED) -> None:
    """
    Safeguard ensuring single-worker execution (SEC-01).
    Validates process/environment settings to prevent split-brain in-memory state.
    """
    worker_env_vars = ["WEB_CONCURRENCY", "UVICORN_WORKERS", "WORKERS"]
    for var in worker_env_vars:
        val = os.getenv(var)
        if val:
            try:
                num = int(val)
                if num > max_allowed:
                    raise RuntimeError(
                        f"Unsupported multi-worker configuration detected ({var}={num}). "
                        f"The ROS Private Server currently maintains in-memory lobby, room, and "
                        f"matchmaking state which requires single-worker operation (max_workers={max_allowed}). "
                        f"Running multiple worker processes causes state desynchronization. "
                        f"Please set {var}=1 or configure an external coordinator (Redis/KeyDB)."
                    )
            except ValueError:
                pass

def perform_system_cleanup() -> Dict[str, Any]:
    """
    Synchronous / deterministic cleanup trigger (SEC-03, SEC-04).
    Prunes stale lobby presences, closed/expired rooms, and expired matchmaking tickets.
    """
    stale_presences = LobbyService.get_instance().cleanup_stale_presences()
    pruned_rooms = RoomService.get_instance().cleanup_stale_rooms()
    pruned_tickets = MatchmakingService.get_instance().cleanup_expired_tickets()
    return {
        "stale_presences_purged": len(stale_presences),
        "rooms_purged": pruned_rooms,
        "tickets_purged": pruned_tickets
    }

async def _periodic_cleanup_loop():
    """Background task running periodic memory cleanup at configured interval."""
    interval = settings.CLEANUP_INTERVAL_SECONDS
    try:
        while True:
            await asyncio.sleep(interval)
            try:
                res = perform_system_cleanup()
                if any(v > 0 for v in res.values()):
                    logger.debug(f"System memory cleanup executed: {res}")
            except Exception as e:
                logger.error(f"Error during periodic cleanup: {e}", exc_info=True)
    except asyncio.CancelledError:
        pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    setup_logging()
    
    if settings.WORKER_GUARD_ENABLED:
        validate_single_worker_configuration()
        logger.info("Worker safeguard verified: single-worker state consistency active.")

    logger.info("Initializing ROS Private Server database schema...")
    await init_db()
    logger.info("Database schema initialized successfully.")

    # Start controlled background cleanup worker
    cleanup_task = asyncio.create_task(_periodic_cleanup_loop())
    logger.info(f"ROS Private Server running on http://{settings.HOST}:{settings.PORT}")
    
    yield
    
    # Shutdown actions
    logger.info("Cancelling background cleanup worker...")
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    logger.info("Shutting down ROS Private Server...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Independent private server foundation for Rules of Survival (ROS) research and multiplayer architecture.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration: Bearer tokens do not need allow_credentials=True with wildcard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global error handler
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled server error on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error."}
    )

# Healthcheck endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "database": "connected"
    }

# Register modular sub-routers
app.include_router(discovery_router)
app.include_router(account_router, prefix=settings.API_V1_PREFIX)
app.include_router(player_router, prefix=settings.API_V1_PREFIX)
app.include_router(lobby_router, prefix=settings.API_V1_PREFIX)
app.include_router(room_router, prefix=settings.API_V1_PREFIX)
app.include_router(matchmaking_router, prefix=settings.API_V1_PREFIX)
app.include_router(admin_router, prefix=settings.API_V1_PREFIX)
