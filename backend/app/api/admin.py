from fastapi import APIRouter, Header, HTTPException, Query

from ..config import settings
from ..services.refresh_service import trigger_refresh


router = APIRouter(tags=["admin"])


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        return ""
    prefix = "bearer "
    if authorization.lower().startswith(prefix):
        return authorization[len(prefix):].strip()
    return ""


def _validate_admin_refresh_token(authorization: str | None, token_query: str | None) -> tuple[bool, list[str]]:
    expected_token = settings.admin_refresh_token
    if not expected_token:
        return True, ["admin_refresh_token_not_set_dev_mode"]

    bearer_token = _extract_bearer_token(authorization)
    provided_token = bearer_token or (token_query or "").strip()
    if provided_token != expected_token:
        raise HTTPException(status_code=401, detail="Invalid admin refresh token")
    return True, []


@router.api_route("/admin/refresh", methods=["GET", "POST"])
def refresh_data(
    scope: str = Query(default="home"),
    token: str | None = Query(default=None),
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    try:
        _, auth_warnings = _validate_admin_refresh_token(authorization, token)
        payload = trigger_refresh(scope=scope)
        if auth_warnings:
            if scope in {"all", "home"}:
                home_payload = payload.get("home")
                if isinstance(home_payload, dict):
                    warnings = list(home_payload.get("warnings", []))
                    home_payload["warnings"] = warnings + auth_warnings
            if scope in {"all", "signal_pool"}:
                signal_payload = payload.get("signal_pool")
                if isinstance(signal_payload, dict):
                    warnings = list(signal_payload.get("warnings", []))
                    signal_payload["warnings"] = warnings + auth_warnings
        return payload
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Refresh failed: {exc}") from exc
