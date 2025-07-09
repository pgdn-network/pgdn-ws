# pgdn-ws

A lightweight WebSocket notification library for FastAPI applications.

## Features

- 🚀 Easy integration with FastAPI
- 🔐 Built-in authentication support
- 👥 User and group-based notifications
- 📨 Simple Python API for sending notifications
- 🔄 Automatic reconnection handling
- 📊 Connection statistics
- 🎯 Custom message handlers
- 💪 Type-safe with Pydantic
- 🐛 **NEW: Sync methods for Celery compatibility**

## Installation

```bash
pip install pgdn-ws
```

## Quick Start

### Basic Usage (Async)

```python
from fastapi import FastAPI
from pgdn_ws import create_websocket_router, notify

app = FastAPI()

# Add WebSocket endpoint
app.include_router(create_websocket_router())

# Send notifications anywhere in your app
@app.post("/trigger")
async def trigger_notification():
    await notify.notify_user(
        user_id="user-123",
        message_type="info",
        payload={"message": "Hello from pgdn-ws!"}
    )
    return {"status": "sent"}
```

### Celery Integration (Sync)

```python
from celery import Celery
from pgdn_ws import notify

celery_app = Celery('myapp')

@celery_app.task
def send_notification_task(user_id: str, message: str):
    # Use sync method - safe for Celery workers
    notify.notify_user_sync(
        user_id=user_id,
        message_type="info",
        payload={"message": message}
    )
    return {"success": True}
```

## Advanced Usage

### Custom Authentication

```python
from pgdn_ws import create_websocket_router

async def my_auth_handler(token: str) -> Optional[Dict[str, Any]]:
    # Verify your JWT/token here
    user = await verify_token(token)
    if user:
        return {
            "user_id": user.id,
            "groups": user.groups
        }
    return None

app.include_router(
    create_websocket_router(auth_handler=my_auth_handler)
)
```

### Group Notifications

```python
# Send to all users in a group (async)
await notify.notify_group(
    group_id="admins",
    message_type="warning",
    payload={"message": "System maintenance in 5 minutes"}
)

# Send to all users in a group (sync - for Celery)
notify.notify_group_sync(
    group_id="admins",
    message_type="warning",
    payload={"message": "System maintenance in 5 minutes"}
)
```

### Broadcast to All

```python
# Broadcast to all connected users (async)
await notify.broadcast(
    message_type="announcement",
    payload={"message": "New feature released!"}
)

# Broadcast to all connected users (sync - for Celery)
notify.broadcast_sync(
    message_type="announcement",
    payload={"message": "New feature released!"}
)
```

### Custom Message Handlers

```python
from pgdn_ws import notification_manager

async def handle_subscribe(message: dict, user_id: str):
    channels = message.get("channels", [])
    # Your subscription logic here
    print(f"User {user_id} subscribed to {channels}")

notification_manager.register_handler("subscribe", handle_subscribe)
```

## Celery Integration

The library now provides sync methods that are safe to use in Celery workers:

### Available Sync Methods

- `notify.notify_user_sync(user_id, message_type, payload)` - Send to specific user
- `notify.notify_users_sync(user_ids, message_type, payload)` - Send to multiple users
- `notify.notify_group_sync(group_id, message_type, payload)` - Send to group
- `notify.broadcast_sync(message_type, payload, exclude_users)` - Broadcast to all

### Example Celery Task

```python
from celery import Celery
from pgdn_ws import notify
import time

celery_app = Celery('myapp')

@celery_app.task
def process_long_task(user_id: str, task_name: str):
    """Long-running task with progress updates"""
    
    # Send start notification
    notify.notify_user_sync(
        user_id=user_id,
        message_type="task_started",
        payload={"task_name": task_name, "progress": 0}
    )
    
    # Simulate work with progress updates
    for progress in range(10, 101, 10):
        time.sleep(2)  # Simulate work
        
        notify.notify_user_sync(
            user_id=user_id,
            message_type="task_progress",
            payload={"task_name": task_name, "progress": progress}
        )
    
    # Send completion notification
    notify.notify_user_sync(
        user_id=user_id,
        message_type="task_completed",
        payload={"task_name": task_name, "progress": 100}
    )
    
    return {"success": True}
```

### When to Use Sync vs Async Methods

- **Use async methods** (`notify.notify_user`, etc.) in FastAPI endpoints for immediate responses
- **Use sync methods** (`notify.notify_user_sync`, etc.) in Celery tasks and background workers

## Frontend Integration

Connect from your frontend:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws?token=' + authToken);

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    console.log('Notification:', message);

    // Handle different message types
    switch(message.type) {
        case 'info':
            showInfoToast(message.payload.message);
            break;
        case 'task_progress':
            updateProgress(message.payload);
            break;
        case 'task_completed':
            showSuccess(message.payload);
            break;
    }
};
```

## Distributed WebSocket Session Tracking with Redis and Celery

For large-scale deployments with multiple WebSocket servers, you can use Redis to track which server each client is connected to. This enables efficient message routing and robust cleanup of stale connections, especially in environments with preemptible servers.

### 1. Install Redis Dependency

```bash
pip install 'redis>=4.2.0'
```

### 2. Track Client Connections with RedisSessionTracker

Use the provided `RedisSessionTracker` utility:

```python
from pgdn_ws.redis_session import RedisSessionTracker
import asyncio

tracker = RedisSessionTracker(redis_url="redis://localhost:6379/0")
await tracker.connect()

# On client connect:
await tracker.register_client(client_id, server_id, ttl=60)

# On client disconnect:
await tracker.unregister_client(client_id)

# Start heartbeat (recommended for preemptible servers):
asyncio.create_task(tracker.heartbeat(lambda: list_of_connected_client_ids(), server_id, ttl=60, interval=30))

# On job arrival:
owner = await tracker.get_client_server(client_id)
if owner == server_id:
    # Deliver to local client
    ...
```

- Each server should have a unique `server_id` (hostname, IP, or UUID).
- The heartbeat ensures that if a server is preempted or crashes, its client mappings expire automatically.

### 3. Server Heartbeat for Liveness

Each WebSocket server should also set a heartbeat key to indicate it is alive:

```python
# In each WebSocket server, run this periodically (e.g., every 30s)
async def server_heartbeat(redis, server_id, ttl=60):
    while True:
        await redis.set(f"ws_server:{server_id}", "alive", ex=ttl)
        await asyncio.sleep(ttl // 2)
```

### 4. Celery Cleanup Job for Stale Mappings

Use Celery to periodically clean up stale client-server mappings in Redis:

```python
# cleanup.py
from celery import Celery
import redis.asyncio as redis
import asyncio

celery_app = Celery('cleanup', broker='redis://localhost:6379/0')

@celery_app.task
def cleanup_stale_clients():
    async def _cleanup():
        r = await redis.from_url("redis://localhost:6379/0", decode_responses=True)
        keys = await r.keys("ws_client:*")
        for key in keys:
            server_id = await r.get(key)
            if not server_id:
                continue
            server_alive = await r.exists(f"ws_server:{server_id}")
            if not server_alive:
                print(f"Cleaning up stale client mapping: {key} (was on {server_id})")
                await r.delete(key)
        await r.close()
    asyncio.run(_cleanup())
```

- Schedule this Celery task to run every few minutes.
- This ensures that if a server dies unexpectedly, any client mappings pointing to it are removed.

### 5. Best Practices

- Use a short TTL (e.g., 60 seconds) for both client and server keys.
- Refresh TTLs frequently (every 30 seconds) via heartbeat.
- Use unique, stable `server_id` values for each server instance.
- Run the Celery cleanup job on a regular schedule (e.g., every 2-5 minutes).

### 6. Example Workflow

1. **Client connects:** Server registers client in Redis with TTL.
2. **Server heartbeat:** Server sets its own liveness key in Redis with TTL.
3. **Client disconnects:** Server removes client mapping from Redis.
4. **Server crash:** Heartbeat and client keys expire automatically.
5. **Celery cleanup:** Removes any stale client mappings pointing to dead servers.

This pattern ensures robust, scalable, and self-healing WebSocket session tracking across many servers.

## API Reference

### NotificationClient Methods

#### Async Methods (for FastAPI endpoints)
- `notify_user(user_id, message_type, payload)` - Send to specific user
- `notify_users(user_ids, message_type, payload)` - Send to multiple users
- `notify_group(group_id, message_type, payload)` - Send to group
- `broadcast(message_type, payload, exclude_users)` - Broadcast to all

#### Sync Methods (for Celery tasks)
- `notify_user_sync(user_id, message_type, payload)` - Send to specific user
- `notify_users_sync(user_ids, message_type, payload)` - Send to multiple users
- `notify_group_sync(group_id, message_type, payload)` - Send to group
- `broadcast_sync(message_type, payload, exclude_users)` - Broadcast to all

#### Utility Methods
- `get_stats()` - Get connection statistics

### Message Types

Built-in types: `info`, `success`, `warning`, `danger`, `error`

Custom types: Any string you define

## Examples

See the `examples/` directory for complete working examples:

- `basic_example.py` - Basic async usage
- `auth_example.py` - Authentication examples
- `celery_simple_example.py` - **NEW: Simple Celery integration examples**

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.
