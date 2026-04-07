from fastapi import APIRouter

from ..schemas.api_schema import HomeResponse
from ..services.homepage_service import build_homepage_payload


router = APIRouter(tags=["home"])


@router.get("/home", response_model=HomeResponse)
def get_home() -> dict:
    return build_homepage_payload()

