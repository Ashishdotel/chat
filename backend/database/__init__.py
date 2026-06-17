# Makes 'database' a Python package.
# Exposes the most-used symbols so callers can write:
#   from backend.database import get_db, init_db
from backend.database.connection import get_db, init_db, engine