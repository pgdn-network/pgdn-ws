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

## Installation

```bash
pip install pgdn-ws
```

## Quick Start

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

## Advanced Usage

### Custom Authentication

```python
from pgdn_ws import create_websocket_router

async def my_auth_handler(token: str) -> Optional[Dict[str, Any]]:
    # Verify your JWT/token here
    user = verify_token(token)
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
# Send to all users in a group
await notify.notify_group(
    group_id="admins",
    message_type="warning",
    payload={"message": "System maintenance in 5 minutes"}
)
```

### Broadcast to All

```python
# Broadcast to all connected users
await notify.broadcast(
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
        case 'scan_progress':
            updateProgress(message.payload);
            break;
    }
};
```

## API Reference

### NotificationClient Methods

- `notify_user(user_id, message_type, payload)` - Send to specific user
- `notify_users(user_ids, message_type, payload)` - Send to multiple users
- `notify_group(group_id, message_type, payload)` - Send to group
- `broadcast(message_type, payload, exclude_users)` - Broadcast to all
- `get_stats()` - Get connection statistics

### Message Types

Built-in types: `info`, `success`, `warning`, `danger`, `error`

Custom types: Any string you define

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.
