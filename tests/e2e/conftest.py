import pytest

from reality import db


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    # Deliberately duplicated from tests/persistence/conftest.py rather than
    # restructured: the e2e suite stays independent of the persistence suite.
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.initialize_database()