"""
Test isolation (v1.1). v1.0 tests shared the developer's real data/storage database, so
test_auth_flow failed on a fresh checkout ("no such table: users") and passed only after other
tests had created the schema. Every test session now gets its own temporary data directory,
configured *before* the application is imported.
"""
import os
import tempfile

os.environ["ML_DATA_DIR"] = tempfile.mkdtemp(prefix="memory_lane_test_")
os.environ.setdefault("ML_LLM_BACKEND", "deterministic")  # never call paid APIs from unit tests

import pytest  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _fresh_schema():
    from app.core.database import init_db
    init_db()
    yield
