# Migration Guide: pgdn-ws v0.1.0 to v0.2.0

This guide helps you migrate from pgdn-ws v0.1.0 to v0.2.0, which introduces sync methods for Celery compatibility.

## What's New

### ✅ Backward Compatibility
All existing async methods continue to work exactly as before. No breaking changes to existing code.

### 🆕 New Sync Methods
New sync methods are available for Celery compatibility:

- `notify.notify_user_sync()` - Sync version of `notify.notify_user()`
- `notify.notify_users_sync()` - Sync version of `notify.notify_users()`
- `notify.notify_group_sync()` - Sync version of `notify.notify_group()`
- `notify.broadcast_sync()` - Sync version of `notify.broadcast()`

## The Problem

If you were using the async methods in Celery tasks like this:

```python
# ❌ This doesn't work in Celery
@celery_app.task
def send_notification(user_id: str, message: str):
    await notify.notify_user(user_id, "info", {"message": message})  # Error!
```

## The Solution

Use the new sync methods in Celery tasks:

```python
# ✅ This works in Celery
@celery_app.task
def send_notification(user_id: str, message: str):
    notify.notify_user_sync(user_id, "info", {"message": message})  # Works!
    return {"success": True}
```

## Migration Steps

### 1. Update the Package

```bash
pip install --upgrade pgdn-ws
```

### 2. No Changes Needed for FastAPI Endpoints

Your existing FastAPI code continues to work:

```python
@app.post("/notify")
async def send_notification():
    await notify.notify_user(
        user_id="user-123",
        message_type="info",
        payload={"message": "Hello!"}
    )
    return {"status": "sent"}
```

### 3. Update Celery Tasks

Replace async calls with sync calls in your Celery tasks:

```python
# Before (doesn't work in Celery)
@celery_app.task
def background_notification(user_id: str, message: str):
    await notify.notify_user(user_id, "info", {"message": message})

# After (works in Celery)
@celery_app.task
def background_notification(user_id: str, message: str):
    notify.notify_user_sync(user_id, "info", {"message": message})
```

## Examples

### Progress Updates from Long-Running Tasks

```python
@celery_app.task
def process_long_task(user_id: str, task_name: str):
    # Send start notification
    notify.notify_user_sync(
        user_id=user_id,
        message_type="task_started",
        payload={"task_name": task_name, "progress": 0}
    )
    
    # Simulate work with progress updates
    import time
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

### Broadcasting from Background Tasks

```python
@celery_app.task
def send_announcement(message: str):
    notify.broadcast_sync(
        message_type="announcement",
        payload={"message": message}
    )
    return {"success": True}
```

## Breaking Changes

**None!** This is a fully backward-compatible release.

## When to Use Which Method

- **Async methods** (`notify.notify_user`, etc.): Use in FastAPI endpoints for immediate responses
- **Sync methods** (`notify.notify_user_sync`, etc.): Use in Celery tasks and background workers

## Examples

See `examples/celery_simple_example.py` for complete working examples.

## Support

If you encounter any issues during migration, please open an issue on GitHub. 