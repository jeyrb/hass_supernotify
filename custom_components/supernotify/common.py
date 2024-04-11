"""
Miscellaneous helper functions.

No dependencies permitted
"""


def safe_get(probably_a_dict, key, default=None):
    probably_a_dict = probably_a_dict or {}
    return probably_a_dict.get(key, default)


def safe_extend(target, extension):
    if isinstance(extension, (list, tuple)):
        target.extend(extension)
    elif extension:
        target.append(extension)
    return target


def ensure_list(v):
    if v is None:
        return []
    if isinstance(v, list):
        return v
    if isinstance(v, tuple):
        return list(v)
    return [v]


def ensure_dict(v, default=None):
    if v is None:
        return {}
    if isinstance(v, dict):
        return v
    if isinstance(v, (set, list)):
        return {vv: default for vv in v}
    return {v: default}
