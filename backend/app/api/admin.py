from fastapi import APIRouter, HTTPException

from ..services.refresh_service import trigger_refresh


router = APIRouter(tags=["admin"])


@router.post("/admin/refresh")
def refresh_data() -> dict[str, object]:
    try:
        return trigger_refresh()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Refresh failed: {exc}") from exc
