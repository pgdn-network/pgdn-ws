# pgdn_ws/router.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from typing import Optional
import json
import logging
from .manager import notification_manager
from .auth import default_auth_handler
from .types import AuthHandler

logger = logging.getLogger("pgdn-notify")
logger.setLevel(logging.INFO)

def create_websocket_router(
    auth_handler: Optional[AuthHandler] = None,
    path: str = "/ws"
) -> APIRouter:
    """Create a WebSocket router with authentication"""
    
    router = APIRouter()
    auth_fn = auth_handler or default_auth_handler
    
    @router.websocket(path)
    async def websocket_endpoint(
        websocket: WebSocket,
        token: Optional[str] = Query(None)
    ):
        logger.info(f"WebSocket connection attempt with token: {token}")
        
        # Authenticate
        user_info = None
        try:
            if not token:
                logger.warning("No token provided")
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing token")
                return
            
            user_info = await auth_fn(token)
            logger.info(f"Auth result: {user_info.get('user_id')}")
            
            if not user_info:
                logger.warning("Auth failed - invalid token")
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
                return
            
            # Connect
            logger.info(f"Connecting user: {user_info.get('user_id')}")
            await notification_manager.connect(websocket, user_info)
            
            # Handle messages
            while True:
                try:
                    data = await websocket.receive_text()
                    logger.info(f"Received message: {data}")
                    message = json.loads(data)
                    await notification_manager.handle_message(websocket, message)
                    
                except WebSocketDisconnect:
                    logger.info("WebSocket disconnected normally")
                    break
                except json.JSONDecodeError:
                    logger.error("Invalid JSON received")
                    await websocket.send_json({
                        "type": "error",
                        "message": "Invalid JSON"
                    })
                except Exception as e:
                    logger.error(f"WebSocket error: {e}", exc_info=True)
                    break
                    
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}", exc_info=True)
        finally:
            if user_info:
                logger.info(f"Cleaning up connection for user: {user_info.get('user_id')}")
            notification_manager.disconnect(websocket)
    
    return router
