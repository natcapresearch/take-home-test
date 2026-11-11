import os
import uuid
from collections.abc import Callable, Generator
from datetime import datetime
from typing import Any, Protocol

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest import FixtureRequest, fixture
from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    Integer,
    String,
    inspect,
    pool,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column
from src.backend.app import deps
from src.backend.app.access import Access, SafeSession
from src.backend.app.config import settings
from src.backend.app.database import DatabaseFactory, Session
from src.backend.app.models.base import (
    BaseModel,
    DeclarativeBase,
)
from src.backend.app.models.change_set import Change, ChangeSet
from src.backend.app.models.commodity_location_entity import (
    CommodityLocationEntity,
)
from src.backend.app.models.export.exported_commodity_location import (
    ExportedCommodityLocation,
)
from src.backend.app.models.organisation import Organisation
from src.backend.app.schemas.organisation import (
    OrganisationConfig,
    OrganisationDB,
)
from src.backend.app.schemas.permission.policy_document import policy_document
from src.backend.app.schemas.user import User
from src.backend.app.util import context
from src.backend.app.util.enums import ChangeSetState

logger = settings.logger


DATABASE_NAME = "backend_test"


@fixture(scope="session")
def worker_id(request: FixtureRequest) -> str:
    """Get the pytest-xdist worker ID for parallel test execution.

    Returns 'master' for non-parallel runs, or 'gw0', 'gw1', etc. for workers.
    """
    if hasattr(request.config, "workerinput"):
        return request.config.workerinput["workerid"]  # type: ignore[no-any-return]
    return "master"


@fixture(scope="session")
def database_name(worker_id: str) -> str:
    """Generate a unique database name scoped to this pytest invocation.

    Appends the master process PID so that two concurrent pytest sessions
    never share the same database, even when both assign the same xdist
    worker IDs.
    """
    session_pid = os.getppid() if worker_id != "master" else os.getpid()
    return f"{DATABASE_NAME}_{worker_id}_{session_pid}"


@fixture(scope="function", autouse=True)
def reset_request_context():
    logger.debug("Resetting request context")
    context.reset_context()


@fixture(scope="function")
def test_user() -> User:
    return User(
        uid="demo|admin@example.com",
        email="admin@example.com",
        roles=["admin"],
        nickname="admin",
    )


@fixture(scope="function")
def test_viewer_user() -> User:
    return User(
        uid="demo|viewer@example.com",
        email="viewer@example.com",
        roles=["viewer"],
        nickname="viewer",
    )


@fixture(scope="function")
def test_admin_access(test_user: User, test_db: DatabaseFactory) -> Access:
    return Access(
        policy_document=policy_document,
        user=test_user,
        database_factory=test_db,
    )


@fixture(scope="function")
def test_viewer_access(
    test_viewer_user: User, test_db: DatabaseFactory
) -> Access:
    return Access(
        policy_document=policy_document,
        user=test_viewer_user,
        database_factory=test_db,
    )


@fixture(scope="function")
def test_admin_session(
    test_admin_access: Access,
) -> Generator[SafeSession]:
    with test_admin_access.get_session() as session:
        yield session


@fixture(scope="function")
def test_viewer_session(
    test_viewer_access: Access,
) -> Generator[SafeSession]:
    with test_viewer_access.get_session() as session:
        yield session


@fixture(scope="function")
def test_org() -> OrganisationDB:
    """Create a test organisation with default values."""
    return OrganisationDB(
        name="Example Org",
        authorised_email_domains=["example.com"],
        config=OrganisationConfig(has_commodity_impacts=True),
    )


@fixture(scope="function")
def test_org_orm(
    test_db_session: Session, test_org: OrganisationDB
) -> Generator[Organisation, None, None]:
    session = test_db_session
    org_orm = Organisation(**test_org.model_dump())
    session.add(org_orm)
    session.commit()
    yield org_orm


# Factories for ORM rows. Each takes the caller's session so the row lands in
# the same transaction as the org (and anything else) it references.
@fixture(scope="function")
def make_org_orm(
    set_up_test_db: None, test_db_session: Session, test_org: OrganisationDB
) -> Callable[[OrganisationDB], Organisation]:
    def _make_org_orm(
        org: OrganisationDB = test_org,
    ) -> Organisation:
        org_orm = test_db_session.get(Organisation, org.uid)
        if org_orm is not None:
            return org_orm

        org_orm = Organisation(
            # We rely on the custom SQLAlchemy field to dump by alias,
            # so we exclude the config field from the model_dump here.
            **org.model_dump(exclude={"config"}),
            config=org.config,
        )
        test_db_session.add(org_orm)
        test_db_session.commit()

        return org_orm

    return _make_org_orm


@fixture(scope="function")
def make_change_set() -> Callable[..., ChangeSet]:
    """Factory for ChangeSet rows. Flushes rather than commits, matching the
    access SafeSession usage in the v2 tests."""

    def _make_change_set(
        session: Session,
        org_uid: uuid.UUID,
        *,
        state: ChangeSetState = ChangeSetState.DONE,
        parent_uid: uuid.UUID | None = None,
    ) -> ChangeSet:
        change_set = ChangeSet(
            org_uid=org_uid, state=state, parent_uid=parent_uid
        )
        session.add(change_set)
        session.flush()
        return change_set

    return _make_change_set


ChangeSetEnv = tuple[uuid.UUID, uuid.UUID]


@fixture(scope="function")
def components_env(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    make_org_orm: Callable[..., Organisation],
    make_change_set: Callable[..., ChangeSet],
) -> ChangeSetEnv:
    """(org_uid, change_set_uid): an org with a change set, for tests that
    record rows into a change set."""
    org = make_org_orm()
    change_set = make_change_set(test_admin_session, org.uid)
    return org.uid, change_set.uid


@fixture(scope="function")
def make_creation_change() -> Callable[..., Change]:
    """Factory for the Change that records `row` as created in a change set,
    which is what change-set reads resolve it through."""

    def _make_creation_change(
        session: Session,
        org_uid: uuid.UUID,
        change_set_uid: uuid.UUID,
        row: BaseModel,
    ) -> Change:
        change = Change(
            org_uid=org_uid,
            change_set_uid=change_set_uid,
            model_type=type(row).__tablename__,
            new_uid=row.uid,
            previous_uid=None,
            description=f"Created {row.uid}",
        )
        session.add(change)
        session.flush()
        return change

    return _make_creation_change


@fixture(scope="function")
def make_tombstone_change() -> Callable[..., Change]:
    """Factory for the Change that records `row` as deleted in a change set,
    so it is no longer alive there or in its descendants."""

    def _make_tombstone_change(
        session: Session,
        org_uid: uuid.UUID,
        change_set_uid: uuid.UUID,
        row: BaseModel,
    ) -> Change:
        change = Change(
            org_uid=org_uid,
            change_set_uid=change_set_uid,
            model_type=type(row).__tablename__,
            new_uid=None,
            previous_uid=row.uid,
            description=f"Deleted {row.uid}",
        )
        session.add(change)
        session.flush()
        return change

    return _make_tombstone_change


@fixture(scope="function")
def make_commodity_location_entity() -> Callable[..., CommodityLocationEntity]:
    """Factory for CommodityLocationEntity rows. Not alive in any change set
    until a creation Change records it (see make_creation_change)."""

    def _make_commodity_location_entity(
        session: Session,
        org_uid: uuid.UUID,
        *,
        identifier: str = "C001",
        commodity_type: str = "Crop",
        commodity_subgroup: str = "Cereals",
        commodity_code: str = "WHEAT",
        year_purchased: int = 2024,
        normalised_key: str | None = None,
        supplier: str | None = None,
        product: str | None = None,
        uid: uuid.UUID | None = None,
    ) -> CommodityLocationEntity:
        entity = CommodityLocationEntity(
            **({"uid": uid} if uid else {}),
            org_uid=org_uid,
            identifier=identifier,
            commodity_type=commodity_type,
            commodity_subgroup=commodity_subgroup,
            commodity_code=commodity_code,
            year_purchased=year_purchased,
            normalised_key=normalised_key or identifier.lower(),
            supplier=supplier,
            product=product,
        )
        session.add(entity)
        session.flush()
        return entity

    return _make_commodity_location_entity


@fixture(scope="function")
def make_exported_commodity_location(
    make_creation_change: Callable[..., Change],
) -> Callable[..., ExportedCommodityLocation]:
    """Factory for ExportedCommodityLocation rows.

    `change_set_uid` writes the creation Change that ties the row to that
    change set. Change-set reads resolve rows through these records, so a
    row created without one belongs to no change set and is invisible to
    them.
    """

    def _make_exported_commodity_location(
        session: Session,
        org_uid: uuid.UUID,
        entity_uid: uuid.UUID,
        *,
        commodity_subgroup: str = "Cereals",
        commodity_type: str = "Crop",
        commodity_code: str = "WHEAT",
        year_purchased: int = 2024,
        identifier: str = "C001",
        sourcing_country_name: str | None = "France",
        sourcing_administrative_level_1_name: str | None = None,
        supplier: str | None = "Supplier A",
        product: str | None = "Wheat Product",
        quantity_kilograms: float | None = 1000.0,
        spend: float | None = 500.0,
        created_at: datetime | None = None,
        change_set_uid: uuid.UUID | None = None,
    ) -> ExportedCommodityLocation:
        kwargs: dict[str, Any] = {
            "uid": uuid.uuid4(),
            "org_uid": org_uid,
            "entity_uid": entity_uid,
            "identifier": identifier,
            "commodity_type": commodity_type,
            "commodity_subgroup": commodity_subgroup,
            "commodity_code": commodity_code,
            "year_purchased": year_purchased,
            "sourcing_country_name": sourcing_country_name,
            "sourcing_administrative_level_1_name": (
                sourcing_administrative_level_1_name
            ),
            "supplier": supplier,
            "product": product,
            "quantity_kilograms": quantity_kilograms,
            "spend": spend,
        }
        if created_at is not None:
            kwargs["created_at"] = created_at
        exported = ExportedCommodityLocation(**kwargs)
        session.add(exported)
        session.flush()
        if change_set_uid is not None:
            make_creation_change(session, org_uid, change_set_uid, exported)
        return exported

    return _make_exported_commodity_location


@fixture(scope="function")
def make_commodity_location(
    make_commodity_location_entity: Callable[..., CommodityLocationEntity],
    make_creation_change: Callable[..., Change],
    make_exported_commodity_location: Callable[..., ExportedCommodityLocation],
) -> Callable[..., ExportedCommodityLocation]:
    """Factory for a commodity location alive in `env`'s change set, with
    its exported row recorded there."""

    def _make_commodity_location(
        session: Session,
        env: ChangeSetEnv,
        code: str,
        *,
        identifier: str,
        subgroup: str | None = None,
        country: str | None = "France",
        spend: float | None = None,
    ) -> ExportedCommodityLocation:
        org_uid, change_set_uid = env
        subgroup = subgroup or code.title()
        entity = make_commodity_location_entity(
            session,
            org_uid,
            identifier=identifier,
            commodity_code=code,
            commodity_subgroup=subgroup,
        )
        make_creation_change(session, org_uid, change_set_uid, entity)
        return make_exported_commodity_location(
            session,
            org_uid,
            entity.uid,
            identifier=identifier,
            commodity_code=code,
            commodity_subgroup=subgroup,
            sourcing_country_name=country,
            spend=spend,
            change_set_uid=change_set_uid,
        )

    return _make_commodity_location


@fixture(scope="session", autouse=True)
def mock_model():
    class MockModel(BaseModel):
        __table_args__ = {
            "extend_existing": True
        }  # To make this work as a reusable mock

        a: Mapped[int] = mapped_column(Integer)
        b: Mapped[str] = mapped_column(String)
        c: Mapped[str] = mapped_column(JSON)
        d: Mapped[float | None] = mapped_column(Float, nullable=True)
        created_at: Mapped[datetime] = mapped_column(DateTime)

    return MockModel


class DemoTestClient(TestClient):
    """A test client that runs every request as `user` (or as nobody when
    `user` is None), in place of the DemoUserMiddleware's configured user."""

    def __init__(
        self,
        app: FastAPI,
        monkeypatch: pytest.MonkeyPatch,
        user: User | None,
    ):
        super().__init__(app=app, follow_redirects=True)
        self.monkeypatch = monkeypatch
        self.user = user

    def request(self, *args: Any, **kwargs: Any):
        # DemoUserMiddleware builds its user from the DEMO_USER_* settings on
        # every request, so pointing those at `user` for the duration of the
        # request makes the app run as that user.
        with self.monkeypatch.context() as _m:
            if self.user is not None:
                _m.setattr(settings, "DEMO_USER_EMAIL", self.user.email)
                _m.setattr(settings, "DEMO_USER_NICKNAME", self.user.nickname)
                _m.setattr(
                    settings, "DEMO_USER_ROLES", ",".join(self.user.roles)
                )
            return super().request(*args, **kwargs)


class ClientGetter(Protocol):
    """
    A callback function which creates a subclass of the FastAPI test client with
    injected Pytest fixtures.
    """

    def __call__(
        self,
        app: FastAPI,
        user: User | None = None,
        org: OrganisationDB | None = None,
        no_auth: bool = False,
    ) -> DemoTestClient: ...


@fixture(scope="function")
def get_client(
    test_db: DatabaseFactory,
    test_db_session: Session,
    test_org: OrganisationDB,
    test_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> ClientGetter:
    def client_getter(
        app: FastAPI,
        user: User | None = test_user,
        org: OrganisationDB | None = test_org,
        no_auth: bool = False,
    ) -> DemoTestClient:
        if no_auth:
            user = None

        # Reset dependencies for each test
        app.dependency_overrides = {
            deps.get_unsafe_session: lambda: test_db_session,
            deps.database_factory: lambda: test_db,
        }
        if user is not None:
            app.dependency_overrides[deps.current_user] = lambda: user
        if org is not None:
            app.dependency_overrides[deps.current_org] = lambda: org

        return DemoTestClient(
            app=app,
            monkeypatch=monkeypatch,
            user=user,
        )

    return client_getter


@fixture(scope="function")
def test_db_session(test_db: DatabaseFactory) -> Generator[Session, None, None]:
    for session in test_db.get_session():  # noqa: UP028
        yield session


@fixture(scope="session")
def test_db(database_name: str) -> DatabaseFactory:
    db = DatabaseFactory(
        host=settings.DB_HOST if settings.DB_HOST else "localhost",
        port=settings.DB_PORT,
        database_name=database_name,
        username=settings.DB_USERNAME,
        password=settings.DB_PASSWORD,
        engine_kwargs={
            # QueuePool, not NullPool: reusing connections keeps the suite
            # from exhausting host sockets under xdist. Safe with the DROP
            # DATABASE teardown: `pool_pre_ping` validates a reused
            # connection, and `_teardown_test_db` drops WITH (FORCE), which
            # evicts anything still checked out.
            "poolclass": pool.QueuePool,
            "echo": False,
        },
    )
    logger.info(f"Using test database connection: {db.uri}")
    return db


def _create_test_db(database_name: str = DATABASE_NAME) -> DatabaseFactory:
    logger.info(f"Creating test database {database_name}...")
    test_db = DatabaseFactory(
        host=settings.DB_HOST if settings.DB_HOST else "localhost",
        port=settings.DB_PORT,
        database_name=settings.DB_NAME,
        username=settings.DB_USERNAME,
        password=settings.DB_PASSWORD,
        engine_kwargs={
            "isolation_level": "AUTOCOMMIT",
            "poolclass": pool.NullPool,
            "echo": False,
            "connect_args": {"options": "-c timezone=utc"},
        },
    )
    with test_db.engine.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {database_name}"))
        conn.commit()

        conn.execute(text(f"CREATE DATABASE {database_name}"))
        conn.execute(
            text(f"ALTER DATABASE {database_name} SET TIMEZONE = 'UTC'")
        )
        conn.commit()

    return test_db


def _teardown_test_db(
    test_db: DatabaseFactory, database_name: str = DATABASE_NAME
):
    logger.info(f"Tearing down test database {database_name}...")
    with test_db.engine.connect() as conn:
        conn.execute(text(f"DROP DATABASE {database_name} WITH (FORCE)"))
        conn.commit()


@fixture(scope="session", autouse=True)
def create_test_db(database_name: str) -> Generator[None, None, None]:
    test_db = _create_test_db(database_name)
    yield
    _teardown_test_db(test_db, database_name)


@fixture(scope="function")
def set_up_test_db(
    create_test_db: None, database_name: str
) -> Generator[None, None, None]:
    logger.info("Creating tables...")

    test_db = DatabaseFactory(
        host=settings.DB_HOST if settings.DB_HOST else "localhost",
        port=settings.DB_PORT,
        database_name=database_name,
        username=settings.DB_USERNAME,
        password=settings.DB_PASSWORD,
        engine_kwargs={
            "poolclass": pool.QueuePool,
            "echo": False,
        },
    )

    # UNLOGGED tables skip WAL for data writes, which keeps the DROP
    # DATABASE at teardown cheap.
    for table in DeclarativeBase.metadata.tables.values():
        table._prefixes = ["UNLOGGED"]
    try:
        DeclarativeBase.metadata.create_all(test_db.engine)
    finally:
        # Restore so the shared metadata object is unmodified for other uses.
        for table in DeclarativeBase.metadata.tables.values():
            table._prefixes = []

    insp = inspect(test_db.engine)
    logger.debug(f"We have tables {insp.get_table_names()}")
    test_db.engine.dispose()

    yield

    logger.info("Wiping DB tables...")

    with test_db.engine.connect() as conn:
        conn.execute(
            text(
                """
                    SET session_replication_role = 'replica';
                    TRUNCATE {};
                    SET session_replication_role = 'origin';
                """.format(
                    ",".join(
                        table.name
                        for table in DeclarativeBase.metadata.sorted_tables
                    )
                )
            )
        )
        conn.commit()

    test_db.engine.dispose()
