import os
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_CORS_ALLOWED_ORIGINS = ",".join(
    [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "http://192.168.3.2:5173",
    ]
)
DEFAULT_CORS_ALLOWED_ORIGIN_REGEX = r"^https?://(?:localhost|127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3})(?::\d+)?$"


@dataclass(frozen=True)
class Settings:
    app_name: str = field(default_factory=lambda: os.getenv("APP_NAME", "24H World Facts"))
    api_prefix: str = field(default_factory=lambda: os.getenv("API_PREFIX", "/api"))
    database_path_env: str = field(default_factory=lambda: os.getenv("DATABASE_PATH", ""))
    mock_data_path_env: str = field(default_factory=lambda: os.getenv("MOCK_DATA_PATH", ""))
    cors_allowed_origins_env: str = field(default_factory=lambda: os.getenv("CORS_ALLOWED_ORIGINS", DEFAULT_CORS_ALLOWED_ORIGINS))
    cors_allowed_origin_regex: str = field(
        default_factory=lambda: os.getenv("CORS_ALLOWED_ORIGIN_REGEX", DEFAULT_CORS_ALLOWED_ORIGIN_REGEX)
    )

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parents[2]

    def _resolve_path(self, raw_value: str, fallback: Path) -> Path:
        if not raw_value:
            return fallback

        candidate = Path(raw_value)
        if candidate.is_absolute():
            return candidate
        return self.project_root / candidate

    @property
    def data_dir(self) -> Path:
        return self.database_path.parent

    @property
    def database_path(self) -> Path:
        return self._resolve_path(self.database_path_env, self.project_root / "data" / "app.db")

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.database_path.as_posix()}"

    @property
    def mock_data_path(self) -> Path:
        return self._resolve_path(self.mock_data_path_env, self.project_root / "data" / "mock_cards.json")

    @property
    def cors_allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins_env.split(",") if origin.strip()]


settings = Settings()
