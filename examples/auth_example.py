from fastapi import FastAPI, Depends, HTTPException
from pgdn_ws import notification_manager, create_websocket_router, notify
from typing import Dict, Any, Optional
import jwt
import asyncio
from datetime import datetime, timedelta

app = FastAPI()

# Secret key for JWT
SECRET_KEY = "your-secret-key-here"
ALGORITHM = "HS256"

# JWT auth handler
async def jwt_auth_handler(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id:
            return {
                "user_id": user_id,
                "groups": payload.get("groups", ["users"]),
                "email": payload.get("email")
            }
    except jwt.InvalidTokenError:
        pass
    return None

# Register custom message handlers
async def handle_subscribe(message: dict, user_id: str):
    """Handle node subscription requests"""
    node_ids = message.get("node_ids", [])

    # In real app, store subscriptions in database
    print(f"User {user_id} subscribed to nodes: {node_ids}")

    # Send confirmation
    await notify.notify_user(
        user_id=user_id,
        message_type="subscription_confirmed",
        payload={
            "node_ids": node_ids,
            "message": f"Subscribed to {len(node_ids)} nodes"
        }
    )

notification_manager.register_handler("subscribe", handle_subscribe)

# Add WebSocket with JWT auth
app.include_router(
    create_websocket_router(auth_handler=jwt_auth_handler),
    prefix="/api"
)

# Login endpoint to get JWT token
@app.post("/api/auth/login")
async def login(email: str, password: str):
    # In real app, verify credentials against database
    if password == "demo":  # Demo auth
        token_data = {
            "sub": f"user-{email.split('@')[0]}",
            "email": email,
            "groups": ["users", "admins"] if email.endswith("@admin.com") else ["users"],
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
        return {"access_token": token, "token_type": "bearer"}

    raise HTTPException(status_code=401, detail="Invalid credentials")

# Protected endpoint that sends notifications
@app.post("/api/nodes/{node_id}/scan")
async def start_node_scan(node_id: str, user_id: str = "user-123"):  # Get from JWT in real app
    scan_id = f"scan-{datetime.utcnow().timestamp()}"

    # Notify user scan started
    await notify.notify_user(
        user_id=user_id,
        message_type="scan_started",
        payload={
            "node_id": node_id,
            "scan_id": scan_id,
            "message": f"Scan started for node {node_id}"
        }
    )

    # Notify admin group
    await notify.notify_group(
        group_id="admins",
        message_type="info",
        payload={
            "message": f"User {user_id} started scan on node {node_id}",
            "scan_id": scan_id
        }
    )

    # Simulate scan progress
    async def simulate_scan():
        stages = [
            ("Initializing", 10),
            ("Port scanning", 30),
            ("Vulnerability check", 60),
            ("SSL verification", 80),
            ("Generating report", 100)
        ]

        for stage, progress in stages:
            await asyncio.sleep(2)

            await notify.notify_user(
                user_id=user_id,
                message_type="scan_progress",
                payload={
                    "node_id": node_id,
                    "scan_id": scan_id,
                    "progress": progress,
                    "stage": stage
                }
            )

        # Broadcast completion
        await notify.broadcast(
            message_type="scan_completed",
            payload={
                "node_id": node_id,
                "scan_id": scan_id,
                "trust_score": 95,
                "message": f"Scan completed for node {node_id}"
            },
            exclude_users=[user_id]  # User already notified
        )

    asyncio.create_task(simulate_scan())

    return {"scan_id": scan_id, "status": "started"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
