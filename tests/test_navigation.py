from datetime import date

from navigation import NavigationHistory, temporal_label


def test_navigation_back_forward_and_branch():
    history = NavigationHistory()
    assert history.current is None and history.move(-1) is None
    for day in (1, 2, 3):
        history.record({"day": day, "view": "cycle"})
    assert history.move(-1)["day"] == 2
    assert history.move(1)["day"] == 3
    history.move(-1)
    history.record({"day": 10, "view": "result"})
    assert history.peek(1) is None
    assert [item["day"] for item in history.entries] == [1, 2, 10]


def test_navigation_duplicates_preserve_forward_history():
    history = NavigationHistory()
    history.record({"day": 1})
    history.record({"day": 2})
    history.move(-1)
    history.record({"day": 1})
    assert history.peek(1) == {"day": 2}
    assert len(history.entries) == 2


def test_navigation_is_bounded_and_snapshots_are_copied():
    history = NavigationHistory(limit=3)
    for day in range(10):
        snapshot = {"day": day}
        history.record(snapshot)
        snapshot["day"] = -1
    assert len(history.entries) == 3 and history.index == 2
    assert history.move(-2) == {"day": 7}
    history.current["day"] = -1
    assert history.current["day"] == 7
    assert history.peek(-1) is None


def test_temporal_label_uses_real_calendar_day():
    today = date(2026, 8, 31)
    assert temporal_label(date(2026, 8, 30), today) == "Passé"
    assert temporal_label(today, today) == "Aujourd’hui"
    assert temporal_label(date(2026, 9, 1), today) == "Futur"
