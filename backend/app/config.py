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


def _get_env_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _default_enable_llm_why_it_matters() -> bool:
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


def _load_dotenv_file() -> None:
    project_root = Path(__file__).resolve().parents[2]
    dotenv_path = project_root / ".env"
    if not dotenv_path.exists():
        return

    try:
        lines = dotenv_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        env_key = key.strip()
        if not env_key or env_key in os.environ:
            continue

        env_value = value.strip()
        if len(env_value) >= 2 and env_value[0] == env_value[-1] and env_value[0] in {'"', "'"}:
            env_value = env_value[1:-1]
        os.environ[env_key] = env_value


_load_dotenv_file()


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
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", "").strip())
    openai_model: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini")
    enable_llm_why_it_matters: bool = field(
        default_factory=lambda: _get_env_bool("ENABLE_LLM_WHY_IT_MATTERS", _default_enable_llm_why_it_matters())
    )
    llm_timeout_seconds: float = field(default_factory=lambda: float(os.getenv("LLM_TIMEOUT_SECONDS", "6")))
    llm_cache_path_env: str = field(default_factory=lambda: os.getenv("LLM_CACHE_PATH", ""))

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

    @property
    def llm_cache_path(self) -> Path:
        return self._resolve_path(self.llm_cache_path_env, self.project_root / "data" / "llm_why_it_matters_cache.json")


settings = Settings()
