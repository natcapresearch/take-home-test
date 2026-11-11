import uuid
from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Any, Protocol, TypeVar, cast

from sqlalchemy import Select, func, literal, select, union_all
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.sql.selectable import Subquery
from src.backend.app.access import SafeSession
from src.backend.app.models.base import BaseModel
from src.backend.app.util.change_set import change_set_query


class _ChangeSetExportModel(Protocol):
    """Shape required of an Exported* model to be resolved by changeset: an
    `entity_uid`/`org_uid` FK and a `__matching_columns__` override keyed on
    `entity_uid` (see ExportedCommodityLocation)."""

    entity_uid: InstrumentedAttribute[uuid.UUID | None]
    org_uid: InstrumentedAttribute[uuid.UUID]
    uid: InstrumentedAttribute[uuid.UUID]
    created_at: InstrumentedAttribute[datetime]
    __tablename__: str


T = TypeVar("T")
M = TypeVar("M", bound=_ChangeSetExportModel)


def _as_base_model(export_model: type[M]) -> type[BaseModel]:
    """Bridge the structural bound on `M` to the nominal one `change_set_query`
    declares.

    `M` is bound to `_ChangeSetExportModel`, a Protocol, because what this
    module needs from a model is a *shape* (`entity_uid`, `org_uid`, and a
    `__matching_columns__` override). `change_set_query` takes a nominal
    `type[BaseModel]`. Every Exported* model satisfies both, but Python has no
    intersection type to say so, so the two bounds can't be unified — this
    states the coincidence in one place rather than scattering casts.
    """
    return cast(type[BaseModel], export_model)


# Guard rail, not an expected org size — caps how many alive entity uids a
# single changeset-scoped read will fetch before restricting the export-row
# query.
MAX_ALIVE_ENTITIES = 15_000


def exported_rows_for_changeset_subquery(
    export_model: type[M],
    change_set_uid: uuid.UUID,
    org_uid: uuid.UUID,
    *,
    columns: Sequence[InstrumentedAttribute[Any]] | None = None,
    restrict_to_uids: Sequence[uuid.UUID] | Select[Any] | None = None,
    name: str = "exported_rows_for_changeset",
    cs_chain_name: str | None = None,
) -> Subquery:
    """Resolve, per `entity_uid`, the `export_model` row current as of
    `change_set_uid` — via the same recursive changeset-ancestor walk used
    for CommodityLocationEntity aliveness (`change_set_query`), rather than
    by picking whichever row is newest by `created_at`.

    Requires `export_model.__matching_columns__` to be overridden to
    `[cls.entity_uid]` (the default is `[cls.uid]`, which is wrong for
    Exported* models: an edit/upload writes a new, immutable row per entity
    rather than updating one in place).

    - `columns`: which `export_model` columns to select. Defaults to the
      whole model. Include `export_model.entity_uid` if the caller needs to
      join/group on it downstream.
    - `restrict_to_uids`: optionally narrows to a subset of entity uids
      (e.g. a page of already-paginated entities), either a list/set of
      uuids or a scalar `Select` of entity uids.
    - `cs_chain_name`: the name of its change set chain CTE, per model by
      default. Only needed when another `change_set_query` over the same
      model shares the statement.
    """
    query = change_set_query(
        change_set_uid,
        org_uid,
        _as_base_model(export_model),
        cs_chain_name=cs_chain_name,
    ).where(export_model.org_uid == org_uid)
    if restrict_to_uids is not None:
        uids: Sequence[uuid.UUID] | Select[Any] = (
            restrict_to_uids
            if isinstance(restrict_to_uids, Select)
            else list(restrict_to_uids)
        )
        query = query.where(export_model.entity_uid.in_(uids))
    if columns is not None:
        query = query.with_only_columns(*columns)
    return query.subquery(name)


def model_row_for_change_set(
    safe_session: SafeSession,
    export_model: type[M],
    org_uid: uuid.UUID,
    change_set_uid: uuid.UUID,
    entity_uid: uuid.UUID,
) -> M | None:
    """The single `export_model` row current as of `change_set_uid` for one
    entity, returned as an ORM object.

    Same resolution as `exported_rows_for_changeset_subquery` — nearest change
    set in the ancestor chain wins — but for one entity and hydrated, so a
    caller can copy its columns forward onto a new row. Returns `None` when no
    change set in the chain has a row for the entity.

    Ordered deterministically before `LIMIT 1`: a change set should hold at
    most one row per entity, and returning a stable one (rather than raising)
    keeps a pre-existing duplicate from turning a read into a 500.
    """
    return (
        safe_session.execute(
            change_set_query(
                change_set_uid, org_uid, _as_base_model(export_model)
            )
            .where(export_model.org_uid == org_uid)
            .where(export_model.entity_uid == entity_uid)
            .order_by(export_model.created_at.desc(), export_model.uid)
            .limit(1)
        )
        .scalars()
        .first()
    )


# Never carried onto the copy: identity and timestamps belong to the INSERT.
_UNCOPIED_EXPORT_COLUMNS = frozenset({"uid", "created_at", "updated_at"})


def copy_exported_row_forward(row: M, **overrides: Any) -> M:
    """An unsaved copy of `row`, ready to be recorded into another change set.

    Exported rows are immutable once a change set other than the writer's own
    draft can render them, so every edit that cannot be made in place proceeds
    by copying the row forward and writing a Change record pointing at the
    copy.

    `overrides` replace copied column values, for callers applying an edit in
    the same step as the copy.

    The caller still owns `add`/`flush` and the Change record: `uid` is only
    assigned at INSERT, and a Change written before that flush records
    `new_uid=None` — a tombstone, not a creation.
    """
    model = type(row)
    data: dict[str, Any] = {}
    # `M` is bound to `_ChangeSetExportModel`, which describes the shape this
    # module needs and so does not declare `__table__`. The nominal BaseModel
    # bound does declare it, and `_as_base_model` already exists to state that
    # every Exported* model satisfies both bounds -- so reuse it here rather
    # than reaching through the Protocol for an attribute it never promised.
    for col in _as_base_model(model).__table__.columns:
        if col.key not in _UNCOPIED_EXPORT_COLUMNS:
            data[col.key] = getattr(row, col.key)
    data.update(overrides)
    return model(**data)


def effective_export_rows_subquery(
    export_model: type[M],
    change_set_uid: uuid.UUID,
    org_uid: uuid.UUID,
    *,
    columns: Sequence[InstrumentedAttribute[Any]],
    restrict_to_uids: Sequence[uuid.UUID] | Select[Any],
    name: str,
) -> Subquery:
    """Per entity in `restrict_to_uids`: the `export_model` row current as of
    `change_set_uid`, else its most recent row — one row per entity.

    An entity alive in the changeset resolves a changeset-current row. One
    that is not alive has none, and falls back to the newest row *that
    entity* ever had, so an entity dropped from later versions still shows
    the values it last had. The fallback is
    keyed on "no changeset row resolved" rather than on an explicit aliveness
    set, so an entity that is not alive but still resolves a row through the
    ancestor chain keeps that row - which is at least as correct as its
    newest one, and avoids computing aliveness twice.

    Entities with no `export_model` row at all are absent; callers outer-join
    and default them rather than dropping the entity.

    `columns` must include `export_model.entity_uid` as its first element.
    `restrict_to_uids` is a list of entity uids or a scalar `Select` of them
    (e.g. the listing's own uid projection), so the resolution joins into the
    caller's statement rather than round-tripping uids through Python.
    """
    keys = [col.key for col in columns]
    in_change_set = exported_rows_for_changeset_subquery(
        export_model,
        change_set_uid,
        org_uid,
        restrict_to_uids=restrict_to_uids,
        name=f"{name}_in_change_set",
    )
    uids: Sequence[uuid.UUID] | Select[Any] = (
        restrict_to_uids
        if isinstance(restrict_to_uids, Select)
        else list(restrict_to_uids)
    )
    # Ties on created_at break on uid, as model_row_for_change_set does, so
    # a pre-existing duplicate resolves the same row on every read.
    candidates = union_all(
        select(
            *[in_change_set.c[key] for key in keys],
            in_change_set.c.uid.label("version_uid"),
            in_change_set.c.created_at.label("version_created_at"),
            literal(0).label("precedence"),
        ),
        select(
            *columns,
            export_model.uid.label("version_uid"),
            export_model.created_at.label("version_created_at"),
            literal(1).label("precedence"),
        ).where(
            export_model.org_uid == org_uid,
            export_model.entity_uid.in_(uids),
        ),
    ).subquery(f"{name}_candidates")
    ranked = select(
        *[candidates.c[key] for key in keys],
        func.row_number()
        .over(
            partition_by=candidates.c.entity_uid,
            order_by=(
                candidates.c.precedence,
                candidates.c.version_created_at.desc(),
                candidates.c.version_uid,
            ),
        )
        .label("rn"),
    ).subquery(f"{name}_ranked")
    return (
        select(*[ranked.c[key] for key in keys])
        .where(ranked.c.rn == 1)
        .subquery(name)
    )


def fetch_effective_export_rows(
    safe_session: SafeSession,
    export_model: type[M],
    change_set_uid: uuid.UUID,
    org_uid: uuid.UUID,
    columns: Sequence[InstrumentedAttribute[Any]],
    entity_uids: list[uuid.UUID],
    row_to_value: Callable[[Any], T],
) -> dict[uuid.UUID, T]:
    """`effective_export_rows_subquery` for a list of entity uids, fetched
    and keyed by `entity_uid`.

    `columns` must include `export_model.entity_uid` as its first element.
    `row_to_value` converts each result row into the caller's per-entity
    value/dataclass.
    """
    if not entity_uids:
        return {}
    sub = effective_export_rows_subquery(
        export_model,
        change_set_uid,
        org_uid,
        columns=columns,
        restrict_to_uids=entity_uids,
        name=f"{export_model.__tablename__}_effective",
    )
    rows = safe_session.execute(
        select(*[sub.c[col.key] for col in columns])
    ).all()
    entity_uid_key = columns[0].key
    return {getattr(row, entity_uid_key): row_to_value(row) for row in rows}
