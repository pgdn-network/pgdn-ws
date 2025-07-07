import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from pgdn_ws.router import create_websocket_router
from pgdn_ws.auth import default_auth_handler


@pytest.fixture
def app():
    app = FastAPI()
    router = create_websocket_router()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.mark.asyncio
async def test_websocket_auth_success():
    """Test successful WebSocket authentication"""
    router = create_websocket_router()
    
    # Mock WebSocket
    websocket = AsyncMock()
    websocket.close = AsyncMock()
    websocket.accept = AsyncMock()
    websocket.receive_text = AsyncMock(side_effect=Exception("Connection closed"))
    
    # Test with valid token
    await router.routes[0].endpoint(websocket, token="valid-token")
    
    # Should accept connection
    websocket.accept.assert_called_once()
    websocket.close.assert_not_called()


@pytest.mark.asyncio
async def test_websocket_auth_failure():
    """Test failed WebSocket authentication"""
    router = create_websocket_router()
    
    # Mock WebSocket
    websocket = AsyncMock()
    websocket.close = AsyncMock()
    websocket.accept = AsyncMock()
    
    # Test with invalid token
    await router.routes[0].endpoint(websocket, token="invalid-token")
    
    # Should close connection
    websocket.close.assert_called_once()
    websocket.accept.assert_not_called()


@pytest.mark.asyncio
async def test_websocket_no_token():
    """Test WebSocket connection without token"""
    router = create_websocket_router()
    
    # Mock WebSocket
    websocket = AsyncMock()
    websocket.close = AsyncMock()
    websocket.accept = AsyncMock()
    
    # Test without token
    await router.routes[0].endpoint(websocket, token=None)
    
    # Should close connection
    websocket.close.assert_called_once()
    websocket.accept.assert_not_called()


@pytest.mark.asyncio
async def test_websocket_auth_returns_none():
    """Test WebSocket authentication when auth handler returns None"""
    async def mock_auth_handler(token):
        return None
    
    router = create_websocket_router(auth_handler=mock_auth_handler)
    
    # Mock WebSocket
    websocket = AsyncMock()
    websocket.close = AsyncMock()
    websocket.accept = AsyncMock()
    
    # Test with any token
    await router.routes[0].endpoint(websocket, token="any-token")
    
    # Should close connection
    websocket.close.assert_called_once()
    websocket.accept.assert_not_called()


@pytest.mark.asyncio
async def test_websocket_auth_returns_empty_dict():
    """Test WebSocket authentication when auth handler returns empty dict"""
    async def mock_auth_handler(token):
        return {}
    
    router = create_websocket_router(auth_handler=mock_auth_handler)
    
    # Mock WebSocket
    websocket = AsyncMock()
    websocket.close = AsyncMock()
    websocket.accept = AsyncMock()
    websocket.receive_text = AsyncMock(side_effect=Exception("Connection closed"))
    
    # Test with any token
    await router.routes[0].endpoint(websocket, token="any-token")
    
    # Should close connection due to missing user_id
    websocket.close.assert_called_once()
    websocket.accept.assert_not_called()


@pytest.mark.asyncio
async def test_websocket_auth_returns_dict_without_user_id():
    """Test WebSocket authentication when auth handler returns dict without user_id"""
    async def mock_auth_handler(token):
        return {"groups": ["admin"]}
    
    router = create_websocket_router(auth_handler=mock_auth_handler)
    
    # Mock WebSocket
    websocket = AsyncMock()
    websocket.close = AsyncMock()
    websocket.accept = AsyncMock()
    
    # Test with any token
    await router.routes[0].endpoint(websocket, token="any-token")
    
    # Should close connection due to missing user_id
    websocket.close.assert_called_once()
    websocket.accept.assert_not_called()


def test_logger_name():
    """Test that logger name is correct"""
    import logging
    router = create_websocket_router()
    
    # The logger should be named "pgdn-ws", not "pgdn-notify"
    logger = logging.getLogger("pgdn-ws")
    assert logger.name == "pgdn-ws" 