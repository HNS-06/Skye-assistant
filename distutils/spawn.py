"""Minimal distutils.spawn.find_executable shim using shutil.which."""
import shutil

def find_executable(cmd):
    """Return the path to an executable or None."""
    try:
        return shutil.which(cmd)
    except Exception:
        return None
