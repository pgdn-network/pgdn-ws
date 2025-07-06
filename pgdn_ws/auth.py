from typing import Optional, Dict, Any

async def default_auth_handler(token: str) -> Optional[Dict[str, Any]]:
    """
    Default auth handler - override this with your own implementation

    Should return user info dict with at least:
    - user_id: str
    - groups: List[str] (optional)
    """
    # This is just a placeholder - implement your own logic
    if token == "valid-token":
        return {
            "user_id": "user-123",
            "groups": ["admin", "users"]
        }
    return None
