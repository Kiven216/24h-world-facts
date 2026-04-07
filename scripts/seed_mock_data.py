import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.config import settings
from backend.app.db import init_database, replace_app_meta, replace_final_cards


def main() -> None:
    init_database()
    with settings.mock_data_path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    replace_final_cards(payload["cards"])
    replace_app_meta(payload["meta"])
    print(f"Seeded {len(payload['cards'])} mock cards into {settings.database_path}")


if __name__ == "__main__":
    main()
