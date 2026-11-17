"""Small session-only navigation history; no engine facts or user database."""

from datetime import date


class NavigationHistory:
    def __init__(self, limit=100):
        if limit < 2:
            raise ValueError("History needs at least two entries")
        self.limit = limit
        self.entries = []
        self.index = -1

    @property
    def current(self):
        return dict(self.entries[self.index]) if self.index >= 0 else None

    def record(self, snapshot):
        if snapshot == self.current:
            return
        del self.entries[self.index + 1:]
        self.entries.append(dict(snapshot))
        self.entries = self.entries[-self.limit:]
        self.index = len(self.entries) - 1

    def peek(self, offset):
        index = self.index + offset
        return dict(self.entries[index]) if 0 <= index < len(self.entries) else None

    def move(self, offset):
        snapshot = self.peek(offset)
        if snapshot is not None:
            self.index += offset
        return snapshot


def temporal_label(target, today=None):
    today = today or date.today()
    return "Passé" if target < today else "Futur" if target > today else "Aujourd’hui"
