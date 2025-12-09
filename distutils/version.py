"""Very small subset of distutils.version.LooseVersion.
Used only for basic version comparisons in some third-party libraries.
"""
import re

class LooseVersion:
    def __init__(self, vstring=''):
        self.vstring = str(vstring)
        parts = re.split(r'[\._\-+]', self.vstring)
        parsed = []
        for p in parts:
            if p.isdigit():
                parsed.append(int(p))
            else:
                parsed.append(p)
        self.version = tuple(parsed)

    def _cmp(self, other):
        if not isinstance(other, LooseVersion):
            other = LooseVersion(other)
        if self.version < other.version:
            return -1
        if self.version > other.version:
            return 1
        return 0

    def __lt__(self, other):
        return self._cmp(other) < 0

    def __le__(self, other):
        return self._cmp(other) <= 0

    def __eq__(self, other):
        return self._cmp(other) == 0

    def __ne__(self, other):
        return self._cmp(other) != 0

    def __gt__(self, other):
        return self._cmp(other) > 0

    def __ge__(self, other):
        return self._cmp(other) >= 0

    def __repr__(self):
        return f"LooseVersion('{self.vstring}')"
