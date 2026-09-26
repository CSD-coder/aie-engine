import hashlib, hmac, json
from datetime import UTC, datetime
from fastapi import Header, HTTPException, status
from .config import get_settings

def require_api_key(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    token = authorization.removeprefix("Bearer ")
    settings = get_settings()
    keys = json.loads(settings.engine_api_keys_json)
    # A configured key records permissions, expiry, and revocation state for rotation.
    for key_id, record in keys.items():
        candidate = record.get("secret", "")
        if hmac.compare_digest(token, candidate):
            expires = record.get("expires_at")
            if record.get("status", "active") != "active" or (expires and datetime.fromisoformat(expires).replace(tzinfo=UTC) < datetime.now(UTC)):
                raise HTTPException(status.HTTP_401_UNAUTHORIZED, "API key is inactive or expired")
            return {"key_id": key_id, "permissions": record.get("permissions", ["*"])}
    if not keys and hmac.compare_digest(token, settings.engine_api_secret):
        return {"key_id": "legacy", "permissions": ["*"]}
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid bearer token")

def key_fingerprint(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()[:16]
