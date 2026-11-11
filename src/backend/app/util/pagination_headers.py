from typing import Any

from fastapi import Response
from src.backend.app.schemas.response import CommonResponseHeaders
from src.backend.app.util.pagination import Paginator


def set_pagination_headers(
    response: Response,
    paginator: Paginator,
    headers_model: type[CommonResponseHeaders] = CommonResponseHeaders,
    **extra: Any,
) -> None:
    """
    Sets the `natcap-next-cursor`, `natcap-prev-cursor` and `natcap-total-count` headers
    from a paginator. Pass a `CommonResponseHeaders` subclass as
    `headers_model`, with its extra fields as keyword arguments, to add more
    headers.
    """
    headers = headers_model.model_validate(
        {
            "next_cursor": paginator.next_cursor,
            "prev_cursor": paginator.prev_cursor,
            "total": paginator.total_count,
            **extra,
        }
    )
    response.headers.update(headers.model_dump(by_alias=True))
