"""
Pytest configuration and fixtures for PhotoVault tests
"""

import os
import pytest
from app.db import init_db, close_db


@pytest.fixture(scope="function")
async def db_setup():
    """Initialize a fresh SQLite test database for each test."""
    test_db_path = "./.test_db.sqlite3"
    try:
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
    except Exception:
        pass
    await init_db()
    try:
        yield
    finally:
        await close_db()
        try:
            if os.path.exists(test_db_path):
                os.remove(test_db_path)
        except Exception:
            pass


