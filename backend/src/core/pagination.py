"""Pagination helper for function-based API views."""

from rest_framework.pagination import LimitOffsetPagination


class StandardPagination(LimitOffsetPagination):
    default_limit = 50
    max_limit = 200


def paginate(queryset_or_list, request, transform_fn=None):
    """
    Paginate a queryset or list and return a paginated Response.

    Args:
        queryset_or_list: Django QuerySet or Python list to paginate.
        request: The DRF request (for limit/offset query params and URL building).
        transform_fn: Optional callable applied to each item before serialization.

    Returns:
        Response with shape ``{"count", "next", "previous", "results"}``.
    """
    paginator = StandardPagination()
    page = paginator.paginate_queryset(queryset_or_list, request)
    if page is None:
        page = []
    data = [transform_fn(item) for item in page] if transform_fn else list(page)
    return paginator.get_paginated_response(data)
