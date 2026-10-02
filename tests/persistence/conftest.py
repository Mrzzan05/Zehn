import pytest

from reality import db


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.initialize_database()


@pytest.fixture
def conn():
    with db.transaction() as c:
        yield c