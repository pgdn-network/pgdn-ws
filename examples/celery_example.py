"""
Example demonstrating how to use pgdn-ws with Celery for reliable async processing.
"""

from fastapi import FastAPI, HTTPException
from pgdn_ws import create_websocket_router, notify, NotificationMessage
from celery import Celery
from typing import Dict, Any, Optional
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(title="pgdn-ws Celery Example")

# Add WebSocket endpoint
app.include_router(create_websocket_router())

# Celery app
celery_app = Celery('pgdn_ws_example')
celery_app.config_from_object({
    'broker_url': 'redis://localhost:6379/0',
    'result_backend': 'redis://localhost:6379/0',
    'task_serializer': 'json',
    'accept_content': ['json'],
    'result_serializer': 'json',
    'timezone': 'UTC',
    'enable_utc': True,
})

# Pydantic models for requests
from pydantic import BaseModel

class NotificationRequest(BaseModel):
    user_id: str
    message_type: str
    payload: Dict[str, Any]

class BroadcastRequest(BaseModel):
    message_type: str
    payload: Dict[str, Any]
    exclude_users: Optional[list] = None

class TaskRequest(BaseModel):
    user_id: str
    task_name: str
    parameters: Optional[Dict[str, Any]] = None

# Celery tasks that use sync methods
@celery_app.task
def send_notification_task(user_id: str, message_type: str, payload: Dict[str, Any]):
    """Celery task to send a notification using sync methods"""
    try:
        # Use sync method - this is safe for Celery
        notify.notify_user_sync(
            user_id=user_id,
            message_type=message_type,
            payload=payload
        )
        logger.info(f"Notification sent to {user_id} via Celery")
        return {"success": True, "user_id": user_id}
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")
        return {"success": False, "error": str(e)}

@celery_app.task
def broadcast_message_task(message_type: str, payload: Dict[str, Any], exclude_users: Optional[list] = None):
    """Celery task to broadcast a message using sync methods"""
    try:
        # Use sync method - this is safe for Celery
        notify.broadcast_sync(
            message_type=message_type,
            payload=payload,
            exclude_users=exclude_users
        )
        logger.info(f"Broadcast sent via Celery")
        return {"success": True}
    except Exception as e:
        logger.error(f"Failed to broadcast message: {e}")
        return {"success": False, "error": str(e)}

@celery_app.task
def process_long_running_task(user_id: str, task_name: str, parameters: Optional[Dict[str, Any]] = None):
    """Example of a long-running task that sends progress updates"""
    try:
        # Send initial notification
        notify.notify_user_sync(
            user_id=user_id,
            message_type="task_started",
            payload={
                "task_name": task_name,
                "parameters": parameters,
                "progress": 0,
                "status": "started",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        # Simulate work with progress updates
        import time
        for progress in range(10, 101, 10):
            time.sleep(2)  # Simulate work
            
            notify.notify_user_sync(
                user_id=user_id,
                message_type="task_progress",
                payload={
                    "task_name": task_name,
                    "progress": progress,
                    "status": "running",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        # Send completion notification
        notify.notify_user_sync(
            user_id=user_id,
            message_type="task_completed",
            payload={
                "task_name": task_name,
                "progress": 100,
                "status": "completed",
                "result": "Task completed successfully",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        return {"success": True, "task_name": task_name, "user_id": user_id}
        
    except Exception as e:
        # Send error notification
        notify.notify_user_sync(
            user_id=user_id,
            message_type="task_error",
            payload={
                "task_name": task_name,
                "error": str(e),
                "status": "failed",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        logger.error(f"Task failed: {e}")
        return {"success": False, "error": str(e)}

# FastAPI endpoints that trigger Celery tasks
@app.post("/api/notify")
async def trigger_notification(request: NotificationRequest):
    """Trigger a notification via Celery"""
    # Queue the task
    task = send_notification_task.delay(
        user_id=request.user_id,
        message_type=request.message_type,
        payload=request.payload
    )
    
    return {
        "task_id": task.id,
        "status": "queued",
        "message": f"Notification queued for user {request.user_id}"
    }

@app.post("/api/broadcast")
async def trigger_broadcast(request: BroadcastRequest):
    """Trigger a broadcast via Celery"""
    # Queue the task
    task = broadcast_message_task.delay(
        message_type=request.message_type,
        payload=request.payload,
        exclude_users=request.exclude_users
    )
    
    return {
        "task_id": task.id,
        "status": "queued",
        "message": "Broadcast queued"
    }

@app.post("/api/tasks/start")
async def start_long_task(request: TaskRequest):
    """Start a long-running task via Celery"""
    # Queue the task
    task = process_long_running_task.delay(
        user_id=request.user_id,
        task_name=request.task_name,
        parameters=request.parameters
    )
    
    return {
        "task_id": task.id,
        "status": "started",
        "message": f"Task {request.task_name} started for user {request.user_id}"
    }

@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Get the status of a Celery task"""
    task = celery_app.AsyncResult(task_id)
    
    return {
        "task_id": task_id,
        "status": task.status,
        "result": task.result if task.ready() else None
    }

@app.get("/api/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics"""
    return notify.get_stats()

# Example of using async methods in FastAPI endpoints (for immediate responses)
@app.post("/api/notify/immediate")
async def send_immediate_notification(request: NotificationRequest):
    """Send notification immediately using async method"""
    await notify.notify_user(
        user_id=request.user_id,
        message_type=request.message_type,
        payload=request.payload
    )
    return {"status": "sent", "message": f"Notification sent immediately to {request.user_id}"}

@app.post("/api/broadcast/immediate")
async def send_immediate_broadcast(request: BroadcastRequest):
    """Send broadcast immediately using async method"""
    await notify.broadcast(
        message_type=request.message_type,
        payload=request.payload,
        exclude_users=request.exclude_users
    )
    return {"status": "sent", "message": "Broadcast sent immediately"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 