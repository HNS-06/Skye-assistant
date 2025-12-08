"""
Minimal shim of the deprecated `cgi` module for Python 3.13 compatibility.
This provides the subset of functions commonly required by third-party
libraries (not a full implementation). Implemented functions:
- parse_header(header_value) -> (value, params_dict)

Place this file in the project root so imports like `import cgi` succeed
when running under Python versions that have removed the stdlib `cgi`.
"""
from typing import Tuple, Dict

def parse_header(value: str) -> Tuple[str, Dict[str, str]]:
    """Parse a Content-Type like header into (main_value, params).

    Example: 'text/html; charset=utf-8' -> ('text/html', {'charset': 'utf-8'})
    """
    if not value:
        return '', {}
    parts = value.split(';')
    main = parts[0].strip()
    params = {}
    for param in parts[1:]:
        if '=' in param:
            k, v = param.split('=', 1)
            k = k.strip().lower()
            v = v.strip().strip('"')
            params[k] = v
    return main, params

# Provide a small shim for FieldStorage name to avoid AttributeError in some libs
class FieldStorage:
    def __init__(self, *args, **kwargs):
        raise RuntimeError("FieldStorage is not implemented in this compatibility shim")

__all__ = ["parse_header", "FieldStorage"]
