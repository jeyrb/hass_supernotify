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
    elif isinstance(v, list):
        return v
    elif isinstance(v, tuple):
        return list(v)
    else:
        return [v]

def ensure_dict(v, default=None):
    if v is None:
        return {}
    elif isinstance(v, dict):
        return v
    elif isinstance(v, list):
        return {vv: default for vv in v}
    else:
        return {v: default}
