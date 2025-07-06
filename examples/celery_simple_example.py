"""
Simple example showing how to use pgdn-ws sync methods in Celery tasks.
"""

from celery import Celery
from pgdn_ws import notify

# Your Celery app (this is in your own application, not in this library)
celery_app = Celery('myapp')

@celery_app.task
def send_notification_task(user_id: str, message: str):
    """Celery task that sends a notification using sync method"""
    # Use the sync version - no async/await needed
    notify.notify_user_sync(
        user_id=user_id,
        message_type="info",
        payload={"message": message}
    )
    return {"success": True, "user_id": user_id}

@celery_app.task
def send_progress_updates(user_id: str, task_name: str):
    """Example of a task that sends progress updates"""
    import time
    
    # Send start notification
    notify.notify_user_sync(
        user_id=user_id,
        message_type="task_started",
        payload={"task_name": task_name, "progress": 0}
    )
    
    # Simulate work with progress updates
    for progress in range(10, 101, 10):
        time.sleep(1)  # Simulate work
        
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
    
    return {"success": True, "task_name": task_name}

@celery_app.task
def broadcast_announcement(message: str):
    """Task that broadcasts a message to all users"""
    notify.broadcast_sync(
        message_type="announcement",
        payload={"message": message}
    )
    return {"success": True, "message": message} 