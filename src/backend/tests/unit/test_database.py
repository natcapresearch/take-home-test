import datetime

from sqlalchemy import text
from sqlalchemy.engine import URL, Engine
from sqlalchemy.orm import Session
from src.backend.app.config import settings
from src.backend.app.database import DatabaseFactory

logger = settings.logger


def test_database_factory():
    database_name = "backend_test"
    db = DatabaseFactory(
        database_name=database_name,
    )
    assert db.config.name == database_name
    assert db.config.username is None
    assert db.config.password is None
    assert db.config.host == "localhost"
    assert db.config.port == 5432
    assert isinstance(db.uri, URL)
    assert (
        db.uri.render_as_string()
        == f"postgresql+psycopg2://localhost:5432/{database_name}"
    )
    assert isinstance(db.engine, Engine)
    assert "connect_args" in db.engine_kwargs


def test_database_factory_from_connection_string():
    db = DatabaseFactory.from_connection_string(
        "postgresql://user:secret@db.example:5433/app"
    )
    assert db.config.host == "db.example"
    assert db.config.port == 5433
    assert db.config.name == "app"
    assert db.config.username == "user"
    assert db.config.password is not None
    assert db.config.password.get_secret_value() == "secret"


def test_get_session(test_db_session: Session):
    assert test_db_session
    assert isinstance(test_db_session, Session)


def test_db(test_db_session: Session):
    result = test_db_session.execute(text("SELECT NOW();")).fetchone()
    assert result and result[0]
    assert isinstance(result[0], datetime.datetime)
