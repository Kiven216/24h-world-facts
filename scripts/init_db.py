from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.config import settings
from backend.app.db import init_database


def main() -> None:
    init_database()
    print(f"Initialized database at {settings.database_path}")


if __name__ == "__main__":
    main()

