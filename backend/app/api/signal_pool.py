from fastapi import APIRouter

from ..schemas.api_schema import SignalPoolResponse
from ..services.signal_pool_service import build_signal_pool_payload


router = APIRouter(tags=["signal-pool"])


@router.get("/signal-pool", response_model=SignalPoolResponse)
def get_signal_pool() -> dict:
    payload = build_signal_pool_payload(include_debug_stats=False)
    payload.pop("_debug", None)
    return payload
