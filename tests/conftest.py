import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import db as db_module

# Force SQLite for all tests, ignoring any local .env DATABASE_URL.
os.environ.pop("DATABASE_URL", None)
db_module.DATABASE_URL = None
