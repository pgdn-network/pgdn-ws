from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pgdn_ws import create_websocket_router, notify, notification_manager
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel
import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="pgdn-notify Demo")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for demo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request models
class NotificationRequest(BaseModel):
    message: str

class BroadcastRequest(BaseModel):
    message: str

# Simple auth handler for demo
async def auth_handler(token: str) -> Optional[Dict[str, Any]]:
    logger.info(f"Auth handler called with token: {token}")
    # In real app, verify JWT token here
    if token.startswith("user-"):
        user_info = {
            "user_id": token,
            "groups": ["users"]
        }
        logger.info(f"Auth successful for user: {user_info}")
        return user_info
    logger.warning(f"Auth failed for token: {token}")
    return None

# Add WebSocket endpoint
app.include_router(
    create_websocket_router(auth_handler=auth_handler),
    prefix="/api"
)

# Example endpoints
@app.post("/api/notify/{user_id}")
async def send_notification(user_id: str, request: NotificationRequest):
    """Send a notification to a specific user"""
    logger.info(f"Sending notification to user {user_id}: {request.message}")
    
    # Check current connections
    stats = notification_manager.get_stats()
    logger.info(f"Current WebSocket stats: {stats}")
    
    try:
        await notify.notify_user(
            user_id=user_id,
            message_type="info",
            payload={
                "message": request.message,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        logger.info(f"Notification sent successfully to {user_id}")
        return {"status": "sent", "user_id": user_id, "message": request.message}
    except Exception as e:
        logger.error(f"Error sending notification: {e}")
        return {"status": "error", "error": str(e)}

@app.post("/api/broadcast")
async def broadcast_message(request: BroadcastRequest):
    """Broadcast a message to all connected users"""
    logger.info(f"Broadcasting message: {request.message}")
    
    await notify.broadcast(
        message_type="announcement",
        payload={
            "message": request.message,
            "from": "system",
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    return {"status": "broadcasted", "message": request.message}

@app.get("/api/ws/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics"""
    stats = notify.get_stats()
    logger.info(f"WebSocket stats requested: {stats}")
    return stats

# Simulate a long-running task with progress updates
class TaskRequest(BaseModel):
    user_id: str

@app.post("/api/tasks/start")
async def start_task(request: TaskRequest):
    """Start a task that sends progress updates"""
    task_id = f"task-{int(datetime.utcnow().timestamp())}"
    logger.info(f"Starting task {task_id} for user {request.user_id}")
    
    async def run_task():
        for progress in range(0, 101, 10):
            await asyncio.sleep(1)
            logger.info(f"Task {task_id} progress: {progress}%")
            await notify.notify_user(
                user_id=request.user_id,
                message_type="task_progress",
                payload={
                    "task_id": task_id,
                    "progress": progress,
                    "status": "running" if progress < 100 else "completed"
                }
            )
    
    asyncio.create_task(run_task())
    return {"task_id": task_id}

# Add a simple test endpoint
@app.get("/")
async def root():
    return {
        "message": "pgdn-notify demo server running",
        "stats": notification_manager.get_stats()
    }

# Add a test endpoint to check connections
@app.get("/api/connections")
async def get_connections():
    """Debug endpoint to see current connections"""
    stats = notification_manager.get_stats()
    return {
        "connections": stats,
        "details": {
            "users": stats.get("users", []),
            "total": stats.get("total_connections", 0)
        }
    }

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting pgdn-notify demo server...")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
