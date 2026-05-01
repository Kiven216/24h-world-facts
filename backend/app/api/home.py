from fastapi import APIRouter, Query

from ..schemas.api_schema import HomeResponse
from ..services.homepage_service import build_homepage_payload


router = APIRouter(tags=["home"])


@router.get("/home", response_model=HomeResponse, response_model_exclude_none=True)
def get_home(debug: int = Query(default=0)) -> dict:
    return build_homepage_payload(include_debug=bool(debug))
