"""Deterministic temporal periods derived from the Olney calculation engine."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Iterable


def _as_date(value: date | datetime | str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


class TimelineEngine:
    """Expose cycle periods without duplicating any card calculation formula."""

    def __init__(self, engine):
        self.engine = engine

    @staticmethod
    def _overlaps(period_start: date, period_end: date,
                  range_start: date, range_end: date) -> bool:
        return period_start < range_end and period_end > range_start

    def _decorate(self, item: dict[str, Any], position: int | None) -> dict[str, Any]:
        item["position"] = position
        item["coordinates"] = (
            self.engine.table_coordinates(position) if position else None
        )
        return item

    def get_periods(
        self,
        birth_date: date | datetime | str,
        start_date: date | datetime | str,
        end_date: date | datetime | str,
        levels: Iterable[str] = (
            "life_path", "seven_year", "annual", "fifty_two_day"
        ),
        birth_card_number: int | None = None,
    ) -> list[dict[str, Any]]:
        birth = _as_date(birth_date)
        start = max(birth, _as_date(start_date))
        end = _as_date(end_date)
        requested = set(levels)
        if end <= start or (
            birth_card_number is None and self.engine.is_joker_birth_date(birth)
        ):
            return []

        periods: list[dict[str, Any]] = []
        first_age = self.engine.age(birth, start)
        last_age = self.engine.age(birth, end)

        if "life_path" in requested:
            period_age = (first_age // 13) * 13
            while True:
                period_start = self.engine.anniversary_date(birth, period_age)
                period_end = self.engine.anniversary_date(birth, period_age + 13)
                if period_start >= end:
                    break
                if self._overlaps(period_start, period_end, start, end):
                    state = self.engine.life_path_table(
                        birth, period_start, birth_card_number=birth_card_number
                    )
                    periods.append(self._decorate({
                        "level": "life_path",
                        "start": period_start.isoformat(),
                        "end_exclusive": period_end.isoformat(),
                        "label": state["card"],
                        "card": state["card"],
                        "series_id": state["series_id"],
                        "sequence_planet": state["active_slot"],
                        "age_start": period_age,
                        "age_end": period_age + 12,
                    }, state["position"]))
                period_age += 13

        if "seven_year" in requested:
            block_age = (first_age // 7) * 7
            while True:
                period_start = self.engine.anniversary_date(birth, block_age)
                period_end = self.engine.anniversary_date(birth, block_age + 7)
                if period_start >= end:
                    break
                if self._overlaps(period_start, period_end, start, end):
                    table_number = block_age // 7 + 1
                    periods.append({
                        "level": "seven_year",
                        "start": period_start.isoformat(),
                        "end_exclusive": period_end.isoformat(),
                        "label": f"Tableau {table_number}",
                        "card": None,
                        "series_id": table_number,
                        "sequence_planet": None,
                        "position": None,
                        "coordinates": None,
                    })
                block_age += 7

        for age in range(first_age, last_age + 2):
            annual_start = self.engine.anniversary_date(birth, age)
            annual_end = self.engine.anniversary_date(birth, age + 1)
            if annual_start >= end:
                break
            if annual_end <= start:
                continue

            if "annual" in requested:
                annual_table = self.engine.seven_year_table(
                    birth, annual_start, birth_card_number=birth_card_number
                )
                active_row = annual_table["rows"][age % 7]
                periods.append(self._decorate({
                    "level": "annual",
                    "start": annual_start.isoformat(),
                    "end_exclusive": annual_end.isoformat(),
                    "label": active_row["card"],
                    "card": active_row["card"],
                    "series_id": annual_table["series_id"],
                    "sequence_planet": active_row["slot"],
                    "age": age,
                }, active_row["position"]))

            if "fifty_two_day" in requested:
                boundaries = self.engine.annual_cycle_boundaries(birth, age)
                for index in range(7):
                    period_start = boundaries[index]
                    period_end = boundaries[index + 1]
                    if not self._overlaps(period_start, period_end, start, end):
                        continue
                    state = self.engine.fifty_two_day_table(
                        birth, period_start, birth_card_number=birth_card_number
                    )
                    periods.append(self._decorate({
                        "level": "fifty_two_day",
                        "start": period_start.isoformat(),
                        "end_exclusive": period_end.isoformat(),
                        "label": state["card"],
                        "card": state["card"],
                        "series_id": state["series_id"],
                        "sequence_planet": state["selected_slot"],
                        "age": age,
                        "window_index": index,
                    }, state["position"]))

        if "day" in requested:
            current = start
            while current < end:
                state = self.engine.day_table(
                    birth, current, birth_card_number=birth_card_number
                )
                active_row = state["rows"][state["weekday_position"] - 1]
                periods.append(self._decorate({
                    "level": "day",
                    "start": current.isoformat(),
                    "end_exclusive": (current + date.resolution).isoformat(),
                    "label": state["card"],
                    "card": state["card"],
                    "series_id": state["series_id"],
                    "sequence_planet": active_row["slot"],
                    "weekday_position": state["weekday_position"],
                    "week_index": (current - birth).days // 7,
                }, active_row["position"]))
                current += date.resolution

        return sorted(periods, key=lambda item: (item["start"], item["level"]))

    def get_transitions(self, birth_date, start_date, end_date,
                        levels=("seven_year", "annual", "fifty_two_day"),
                        birth_card_number=None):
        periods = self.get_periods(
            birth_date, start_date, end_date, levels, birth_card_number
        )
        grouped: dict[str, list[dict[str, Any]]] = {}
        for period in periods:
            grouped.setdefault(period["level"], []).append(period)

        transitions = []
        for level, rows in grouped.items():
            rows.sort(key=lambda item: item["start"])
            for previous, current in zip(rows, rows[1:]):
                transitions.append({
                    "date": current["start"],
                    "type": "cycle_change",
                    "cycle": level,
                    "previous_card": previous.get("card"),
                    "new_card": current.get("card"),
                    "previous_label": previous["label"],
                    "new_label": current["label"],
                })
        return sorted(transitions, key=lambda item: item["date"])

    def get_hour_periods(self, start_datetime, end_datetime, place):
        """Return exact minute-level changes of the independent hour card.

        This range is intentionally generated on demand for close timeline
        zooms only; no hourly history is persisted.
        """
        start = start_datetime.replace(second=0, microsecond=0)
        end = end_datetime.replace(second=0, microsecond=0)
        if end <= start or not place:
            return []

        periods = []
        current = start
        active_start = start
        active = None
        while current < end and active is None:
            try:
                active = self.engine.hour_card(
                    current.date(), current.strftime("%H:%M"), place
                )
            except ValueError:
                # A civil minute can be absent during the spring DST jump.
                current += timedelta(minutes=1)
                active_start = current
        if active is None:
            return []
        while current < end:
            current += timedelta(minutes=1)
            if current >= end:
                break
            try:
                state = self.engine.hour_card(
                    current.date(), current.strftime("%H:%M"), place
                )
            except ValueError:
                continue
            if state["card"] == active["card"]:
                continue
            periods.append({
                "level": "hour",
                "start": active_start.isoformat(timespec="minutes"),
                "end_exclusive": current.isoformat(timespec="minutes"),
                "label": active["card"],
                "card": active["card"],
                "sequence_planet": None,
                "position": None,
                "coordinates": None,
                "solar_hour": active["solar_hour"],
            })
            active_start = current
            active = state

        periods.append({
            "level": "hour",
            "start": active_start.isoformat(timespec="minutes"),
            "end_exclusive": end.isoformat(timespec="minutes"),
            "label": active["card"],
            "card": active["card"],
            "sequence_planet": None,
            "position": None,
            "coordinates": None,
            "solar_hour": active["solar_hour"],
        })
        return periods

    def find_card_occurrences(self, birth_date, card, start_date, end_date,
                              levels=None, birth_card_number=None):
        requested = levels or ("annual", "fifty_two_day")
        return [
            period for period in self.get_periods(
                birth_date, start_date, end_date, requested, birth_card_number
            )
            if period.get("card") == card
        ]

    def find_convergences(self, birth_date, start_date, end_date,
                          levels=("annual", "fifty_two_day"),
                          birth_card_number=None):
        periods = self.get_periods(
            birth_date, start_date, end_date, levels, birth_card_number
        )
        convergences = []
        by_card = {}
        for period in periods:
            if period.get("card"):
                by_card.setdefault(period["card"], []).append(period)
        seen = set()
        for card, rows in by_card.items():
            for index, first in enumerate(rows):
                for second in rows[index + 1:]:
                    if first["level"] == second["level"]:
                        continue
                    overlap_start = max(
                        _as_date(first["start"]), _as_date(second["start"])
                    )
                    overlap_end = min(
                        _as_date(first["end_exclusive"]),
                        _as_date(second["end_exclusive"]),
                    )
                    key = (overlap_start, overlap_end, card)
                    if overlap_start >= overlap_end or key in seen:
                        continue
                    seen.add(key)
                    convergences.append({
                        "date": overlap_start.isoformat(),
                        "end_exclusive": overlap_end.isoformat(),
                        "type": "card_return",
                        "card": card,
                        "levels": sorted({first["level"], second["level"]}),
                    })
        return convergences
