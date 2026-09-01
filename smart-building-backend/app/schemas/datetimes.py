"""UTC normalization for timestamps crossing the API boundary.

Timestamps are stored in ``timestamp without time zone`` columns and written by
``utc_now()``, which is ``datetime.now(UTC).replace(tzinfo=None)``. The instant
is UTC but the tzinfo is gone, so a bare ``datetime`` field serializes as
``2026-08-31T16:26:07`` with no offset. ``new Date()`` reads an offset-less
string as local time, which in Tehran shifts a fresh notification 3.5 hours into
the past.

Annotating a response field with :data:`UtcDatetime` stamps UTC as the model is
built, so the JSON carries ``+00:00`` and names an absolute instant. The clock
reading never moves — only the missing offset is restored.
"""

from datetime import UTC, datetime
from typing import Annotated

from pydantic import AfterValidator


def ensure_utc(value: datetime | None) -> datetime | None:
    """Return ``value`` as a UTC-aware datetime without shifting the instant.

    A naive value is assumed to already be UTC, which is what every writer in
    this codebase produces. An aware value is converted, so a field that is
    already aware stays correct.
    """
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


#: A ``datetime`` response field guaranteed to serialize with a UTC offset.
UtcDatetime = Annotated[datetime, AfterValidator(ensure_utc)]
