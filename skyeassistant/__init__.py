"""Compatibility package to allow `import skyeassistant` to load the canonical
`SkyeAssistant.py` implementation regardless of filename case on Windows.
"""
import importlib
_mod = importlib.import_module('SkyeAssistant')
for _name in dir(_mod):
    if not _name.startswith('_'):
        globals()[_name] = getattr(_mod, _name)

# Explicitly expose the main class under the expected name
try:
    SkyeAssistant = _mod.SkyeAssistant
except AttributeError:
    pass
