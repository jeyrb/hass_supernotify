"""Miscellaneous helper functions.

No dependencies permitted
"""

import time
from typing import Any


def format_timestamp(v: float | None) -> str | None:
    return time.strftime("%H:%M:%S", time.localtime(v)) if v else None


def safe_get(probably_a_dict: dict | None, key: Any, default: Any = None) -> Any:
    probably_a_dict = probably_a_dict or {}
    return probably_a_dict.get(key, default)


def safe_extend(target: list, extension: list | tuple | Any) -> list:
    if isinstance(extension, list | tuple):
        target.extend(extension)
    elif extension:
        target.append(extension)
    return target


def ensure_list(v: Any) -> list:
    if v is None:
        return []
    if isinstance(v, list):
        return v
    if isinstance(v, tuple):
        return list(v)
    return [v]


def ensure_dict(v: Any, default: Any = None) -> dict:
    if v is None:
        return {}
    if isinstance(v, dict):
        return v
    if isinstance(v, set | list):
        return dict.fromkeys(v, default)
    return {v: default}
