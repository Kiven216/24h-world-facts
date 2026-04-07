from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_name: str = "24H World Facts"
    api_prefix: str = "/api"

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parents[2]

    @property
    def data_dir(self) -> Path:
        return self.project_root / "data"

    @property
    def database_path(self) -> Path:
        return self.data_dir / "app.db"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.database_path.as_posix()}"

    @property
    def mock_data_path(self) -> Path:
        return self.data_dir / "mock_cards.json"


settings = Settings()

