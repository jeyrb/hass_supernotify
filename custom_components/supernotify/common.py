"""Miscellaneous helper functions.

No dependencies permitted
"""

import time
from dataclasses import dataclass, field
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


def update_dict_list(target: list[dict[Any, Any]], to_add: list[dict], to_remove: list[dict]) -> list[dict]:
    updated = [d for d in target if d not in to_remove]
    updated.extend(to_add)
    return updated


@dataclass
class CallRecord:
    elapsed: float = field()
    domain: str | None = field(default=None)
    service: str | None = field(default=None)
    action_data: dict | None = field(default=None)
    exception: str | None = field(default=None)

    def contents(self) -> tuple:
        if self.exception:
            return (self.domain, self.service, self.action_data, self.exception, self.elapsed)
        return (self.domain, self.service, self.action_data, self.elapsed)


@dataclass
class DebugTrace:
    message: str | None = field(default=None)
    title: str | None = field(default=None)
    data: dict | None = field(default_factory=lambda: {})
    target: list | str | None = field(default=None)
    resolved: dict[str, dict] = field(init=False, default_factory=lambda: {})
    delivery_selection: dict[str, list] = field(default_factory=lambda: {})

    def contents(self) -> tuple:
        return (self.message, self.title, self.data, self.target, self.resolved, self.delivery_selection)
