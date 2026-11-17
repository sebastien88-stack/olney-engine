APP_VERSION = "1.8.9"
"""Single source for application and Windows metadata versions (no dependencies)."""

WINDOWS_VERSION = tuple(map(int, APP_VERSION.split("."))) + (0,)
