"""
RedisSessionTracker: Distributed WebSocket session tracking for pgdn-ws

This utility allows you to track which server each client is connected to in a multi-server environment.
It uses Redis to store mappings of client_id -> server_id, with automatic cleanup via TTL and heartbeat.

Usage:

1. Install redis-py (async support):
   pip install 'redis>=4.2.0'

2. In your FastAPI/WebSocket server:

    from pgdn_ws.redis_session import RedisSessionTracker
    import asyncio

    tracker = RedisSessionTracker(redis_url="redis://localhost:6379/0")
    await tracker.connect()

    # On client connect:
    await tracker.register_client(client_id, server_id, ttl=60)

    # On client disconnect:
    await tracker.unregister_client(client_id)

    # Start heartbeat (optional, recommended for preemptible servers):
    asyncio.create_task(tracker.heartbeat(lambda: list_of_connected_client_ids(), server_id, ttl=60, interval=30))

    # On job arrival:
    owner = await tracker.get_client_server(client_id)
    if owner == server_id:
        # Deliver to local client
        ...

- If a server dies, its client mappings expire after TTL seconds.
- Heartbeat should be called periodically to refresh TTLs for all active clients.

"""
import asyncio
from typing import Callable, List, Optional

try:
    import redis.asyncio as redis
except ImportError:
    redis = None

class RedisSessionTracker:
    def __init__(self, redis_url: str):
        if redis is None:
            raise ImportError("redis-py>=4.2.0 with asyncio support is required. Install with 'pip install redis>=4.2.0'.")
        self.redis_url = redis_url
        self.redis: Optional[redis.Redis] = None

    async def connect(self):
        self.redis = await redis.from_url(self.redis_url, decode_responses=True)

    async def register_client(self, client_id: str, server_id: str, ttl: int = 60):
        """Register a client with a TTL (seconds)."""
        await self.redis.set(f"ws_client:{client_id}", server_id, ex=ttl)

    async def unregister_client(self, client_id: str):
        """Remove a client mapping."""
        await self.redis.delete(f"ws_client:{client_id}")

    async def get_client_server(self, client_id: str) -> Optional[str]:
        """Get the server_id for a client, or None if not found."""
        return await self.redis.get(f"ws_client:{client_id}")

    async def heartbeat(self, get_client_ids: Callable[[], List[str]], server_id: str, ttl: int = 60, interval: int = 30):
        """
        Periodically refresh TTL for all connected clients.
        - get_client_ids: Callable returning the current list of connected client_ids
        - server_id: This server's unique ID
        - ttl: TTL for each mapping (seconds)
        - interval: How often to refresh (seconds)
        """
        while True:
            client_ids = get_client_ids()
            if client_ids:
                pipe = self.redis.pipeline()
                for client_id in client_ids:
                    pipe.set(f"ws_client:{client_id}", server_id, ex=ttl)
                await pipe.execute()
            await asyncio.sleep(interval) 