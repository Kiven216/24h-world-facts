from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.admin import router as admin_router
from .api.health import router as health_router
from .api.home import router as home_router
from .config import settings
from .db import init_database


app = FastAPI(title=settings.app_name)


@app.on_event("startup")
def startup() -> None:
    # Keep staging setup simple by creating the SQLite file and tables on boot.
    init_database()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_origin_regex=settings.cors_allowed_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix=settings.api_prefix)
app.include_router(home_router, prefix=settings.api_prefix)
app.include_router(admin_router, prefix=settings.api_prefix)
