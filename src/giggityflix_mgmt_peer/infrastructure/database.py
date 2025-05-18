# src/peer/infrastructure/database.py
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from ..core.annotations import io_bound


class Database:
    """Simple SQLite database interface with resource management."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        # For in-memory databases, no IO concerns
        if db_path == ':memory:':
            self.conn = sqlite3.connect(db_path)
            self.conn.row_factory = sqlite3.Row
        else:
            # For file-based databases, we'll connect on demand
            self.conn = None

    @io_bound(param_name='db_path')
    def _connect(self, db_path: str) -> sqlite3.Connection:
        """Connect to the database (IO-bound operation)."""
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @io_bound(param_name='db_path')
    def execute(self, db_path: str, query: str, params: Optional[Tuple] = None) -> sqlite3.Cursor:
        """Execute a query (IO-bound operation)."""
        if db_path == ':memory:':
            cursor = self.conn.cursor()
        else:
            # Connect if needed
            if not self.conn:
                self.conn = sqlite3.connect(db_path)
                self.conn.row_factory = sqlite3.Row
            cursor = self.conn.cursor()

        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        if db_path == ':memory:' or self.conn:
            self.conn.commit()

        return cursor

    async def fetch_one(self, query: str, params: Optional[Tuple] = None) -> Optional[Dict[str, Any]]:
        """Fetch a single row from the database."""
        cursor = await self.execute(self.db_path, query, params)
        row = cursor.fetchone()
        return dict(row) if row else None

    async def fetch_all(self, query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """Fetch all rows from the database."""
        cursor = await self.execute(self.db_path, query, params)
        return [dict(row) for row in cursor.fetchall()]

    async def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
