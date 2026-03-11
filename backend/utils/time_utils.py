"""Datetime utilities for VistterStream.

SQLite stores datetime values without timezone info (naive). When comparing
runtime timezone-aware datetimes with values read from the database, Python
raises "can't subtract offset-naive and offset-aware datetimes".

This module provides a helper that returns the current UTC time as a naive
datetime, suitable for comparisons with SQLite-sourced values.
"""

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Return current UTC time as a naive datetime (SQLite-compatible).

    Use this for arithmetic/comparisons with datetimes read from SQLite.
    For storing new values, use ``datetime.now(timezone.utc)`` directly —
    SQLAlchemy will strip the tzinfo when writing to SQLite.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
