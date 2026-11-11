import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from src.backend.app import deps
from src.backend.app.access import Access, SafeSession
from src.backend.app.api.v1 import change_set as change_set_v1
from src.backend.app.errors.errors import (
    ChangeSetNotFoundError,
    NotAuthorisedError,
)
from src.backend.app.models.change_set import ChangeSet
from src.backend.app.schemas.change_set import (
    ChangeSetRead,
    ChangeSetSummary,
)
from src.backend.app.schemas.organisation import OrganisationDB
from src.backend.app.schemas.request import (
    ChangeSetsQueryParams,
    ChangeSetUpdate,
)
from src.backend.app.schemas.response import CommonResponseHeaders
from src.backend.app.util import change_set as change_set_util
from src.backend.app.util.change_set import (
    NON_ADMIN_VISIBLE_CHANGE_SET_STATES,
    can_read_all_change_set_states,
)
from src.backend.app.util.enums import ChangeSetState

change_set_router = APIRouter(
    tags=["change-sets"],
)


@change_set_router.get(
    "/change-sets/",
    response_model=list[ChangeSetRead],
    summary="Get a list of change sets",
)
def get_change_sets(
    response: Response,
    q: Annotated[ChangeSetsQueryParams, Query()],
    safe_session: SafeSession = Depends(deps.get_safe_session),
    org: OrganisationDB = Depends(deps.current_org),
    access: Access = Depends(deps.access),
) -> list[ChangeSetRead]:
    """Get change sets for the given organisation."""
    visible_states = (
        None
        if can_read_all_change_set_states(access)
        else NON_ADMIN_VISIBLE_CHANGE_SET_STATES
    )

    change_sets, paginator = change_set_v1.get_change_sets(
        safe_session,
        org,
        state=q.state,
        visible_states=visible_states,
        cursor=q.before or q.after,
        reverse_pagination=bool(q.before),
        sort_on=q.sort_on or "created_at",
        sort_order=q.sort_order,
        limit=q.limit,
    )

    headers = CommonResponseHeaders.model_validate(
        {
            "next_cursor": paginator.next_cursor,
            "prev_cursor": paginator.prev_cursor,
            "total": paginator.total_count,
        }
    )
    response.headers.update(headers.model_dump(by_alias=True))

    return change_sets


@change_set_router.get(
    "/change-sets/{change_set_uid}/summary/",
    response_model=ChangeSetSummary,
    summary="Get a summary of changes for a change set",
)
def get_change_summary(
    change_set_uid: uuid.UUID,
    safe_session: SafeSession = Depends(deps.get_safe_session),
    org: OrganisationDB = Depends(deps.current_org),
    access: Access = Depends(deps.access),
) -> ChangeSetSummary:
    """Get a grouped summary of changes for the given organisation and change set."""
    change_set_util.get_visible_change_set_or_404(
        safe_session, access, org.uid, change_set_uid
    )

    return change_set_v1.get_change_summary(
        safe_session,
        org_uid=org.uid,
        change_set_uid=change_set_uid,
    )


@change_set_router.get("/change-set/", response_model=ChangeSetRead)
def get_change_set(
    change_set_uid: uuid.UUID | None = None,
    safe_session: SafeSession = Depends(deps.get_safe_session),
    org: OrganisationDB = Depends(deps.current_org),
    access: Access = Depends(deps.access),
) -> ChangeSetRead:
    """Get a change set by UID, or the organisation's default change set.

    The caller must handle 404 responses. An organisation will not have any
    change sets when the org is first created.
    """
    change_set_uid = change_set_uid or org.default_change_set_uid
    if change_set_uid is None:
        raise ChangeSetNotFoundError("Change set not found.")

    change_set = change_set_util.get_visible_change_set_or_404(
        safe_session, access, org.uid, change_set_uid
    )

    return change_set_v1.hydrate_change_set_reads(
        safe_session, org_uid=org.uid, change_sets=[change_set]
    )[0]


@change_set_router.patch(
    "/change-sets/{change_set_uid}/",
    response_model=ChangeSetRead,
    summary="Update the name, description, and/or state of a change set",
)
def patch_change_set(
    change_set_uid: uuid.UUID,
    body: ChangeSetUpdate,
    safe_session: SafeSession = Depends(deps.get_safe_session),
    org: OrganisationDB = Depends(deps.current_org),
    access: Access = Depends(deps.access),
) -> ChangeSet:
    """Update the name, description, and/or state of a change set.

    All body fields are optional. State transitions must follow allowed rules
    (DRAFT→PROCESSING, PROCESSING→DRAFT/DONE, DONE↔PUBLISHED).
    Requires ``update:change_set:basic`` for name/description edits and
    ``update:change_set:publish`` for state transitions.
    """
    if body.state is not None:
        if not access.check("update:change_set:publish", change_set_uid):
            raise NotAuthorisedError(
                "Insufficient permissions to publish or unpublish this change set."
            )
    if not access.check("update:change_set:basic", change_set_uid):
        raise NotAuthorisedError(
            "Insufficient permissions to update this change set."
        )

    change_set = change_set_v1.patch_change_set(
        safe_session,
        org_uid=org.uid,
        change_set_uid=change_set_uid,
        name=body.name,
        description=body.description,
        new_state=ChangeSetState(body.state)
        if body.state is not None
        else None,
    )

    return change_set
