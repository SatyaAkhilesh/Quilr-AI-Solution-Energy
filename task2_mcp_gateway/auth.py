from typing import Optional


TOKEN_ROLES = {
    "admin-token": "admin",
    "viewer-token": "viewer",
}


def get_role(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None

    if not authorization.startswith("Bearer "):
        return None

    token = authorization.removeprefix("Bearer ").strip()

    return TOKEN_ROLES.get(token)