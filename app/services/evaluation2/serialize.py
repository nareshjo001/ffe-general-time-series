"""JSON-safe serialization for raw `handout_adapter` output.

Why this module exists (see the Phase 2 handout audit): `run_real`/`run_pair`
return raw query `value`/`real_value`/`synth_value` objects that are NOT
JSON-safe as-is - they can be Python floats, numpy scalars, numpy arrays,
tuples (the `location` kind), sets (the `set` kind), or NaN/+Inf/-Inf. This
module recursively converts any such structure into something built only
from ``dict``/``list``/``str``/``int``/``float``/``bool``/``None``, so it can
be handed to ``json.dumps(..., allow_nan=False)`` without error.

Deliberately NOT implemented as ``json.dump(..., default=str)`` - stringifying
every non-primitive value would hide type problems (a numpy array silently
becoming its ``repr()`` string, a NaN silently becoming the string ``"nan"``,
which `json.loads` cannot round-trip) instead of solving them. Every
recognized type here converts to its correct JSON-safe *shape*, not to text.

An unrecognized type is a hard error (``TypeError``), not a silent
``str()`` fallback: stringifying a future/unexpected querylib result type
would hide data loss and let a corrupted or incomplete result be persisted
as though serialization had succeeded.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd


def jsonable(value: Any) -> Any:
    """Recursively convert ``value`` into a JSON-safe structure.

    Conversion rules:
        numpy integer            -> int
        numpy float              -> float (NaN/+Inf/-Inf -> None)
        numpy bool_               -> bool
        python float NaN/Inf     -> None
        numpy ndarray (any rank) -> nested list
        tuple                    -> list
        set / frozenset          -> list, sorted for a deterministic order
                                     (falls back to sorting by ``repr`` if the
                                     elements are not natively orderable)
        dict                     -> dict, keys coerced to ``str``, values
                                     converted recursively
        list                     -> list, values converted recursively
        pandas.Timestamp         -> ISO-8601 string
        str / int / bool / None  -> returned unchanged
        anything else            -> raises TypeError (see module docstring)

    Raises:
        TypeError: if ``value`` (or something nested inside it) is not one
            of the types explicitly handled above. This is intentional -
            silently stringifying an unrecognized type would hide data loss.
    """
    if value is None:
        return None

    # bool is a subclass of int in Python - must be checked before int.
    if isinstance(value, bool):
        return value
    if isinstance(value, np.bool_):
        return bool(value)

    if isinstance(value, (int, np.integer)):
        return int(value)

    if isinstance(value, (float, np.floating)):
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return None
        return f

    if isinstance(value, np.ndarray):
        # .tolist() recursively converts every element (including nested
        # sub-arrays) to native Python scalars; re-run through jsonable()
        # so NaN/Inf inside the array are still normalized to None.
        return jsonable(value.tolist())

    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}

    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]

    if isinstance(value, (set, frozenset)):
        try:
            ordered = sorted(value)
        except TypeError:
            ordered = sorted(value, key=repr)
        return [jsonable(v) for v in ordered]

    if isinstance(value, str):
        return value

    if isinstance(value, pd.Timestamp):
        return value.isoformat()

    # Genuinely unrecognized type: fail loudly rather than silently
    # stringifying it. A silent str() fallback here could let a
    # corrupted/incomplete result be persisted as though serialization had
    # succeeded, for a future querylib result type this module doesn't know
    # about yet.
    raise TypeError(
        f"Unsupported value type for JSON serialization: "
        f"{type(value).__module__}.{type(value).__qualname__}"
    )


def rows(df: pd.DataFrame) -> list[dict]:
    """Convert a `handout_adapter` result DataFrame into a list of JSON-safe
    row dicts: ``df.to_dict(orient="records")`` followed by a recursive
    :func:`jsonable` pass over every record. The result is guaranteed to pass
    ``json.dumps(..., allow_nan=False)`` without error.
    """
    return [jsonable(record) for record in df.to_dict(orient="records")]


__all__ = ["jsonable", "rows"]
