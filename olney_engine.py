"""
Olney Engine
================
A Python implementation of the calculation layer represented by
"tableaux suivi des cartes.xlsx".

Important:
- This module calculates; it does not interpret.
- The 90 canonical series are data extracted from Feuil2.
- Card labels come from Feuil3.
- Keep data.json versioned and immutable once validated.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Optional
import json
import math

from hour_card import get_hour_card as calculate_hour_card


PLANETS = ("lune", "soleil", "mercure", "vénus", "mars", "jupiter", "saturne", "uranus", "neptune")
SEVEN_YEAR_PLANETS = ("mercure", "vénus", "mars", "jupiter", "saturne", "uranus", "neptune")
LIFE_PATH_AGE_RANGES = tuple((index * 13, index * 13 + 12) for index in range(7))
OFFSETS = {
    "lune": -1,
    "soleil": 0,
    "mercure": 1,
    "vénus": 2,
    "mars": 3,
    "jupiter": 4,
    "saturne": 5,
    "uranus": 6,
    "neptune": 7,
    "défi": 8,
    "résultat": 9,
}
RULER_OFFSETS = {
    "lune": -1,
    "soleil": 0,
    "mercure": 1,
    "vénus": 2,
    "mars": 3,
    "jupiter": 4,
    "saturne": 5,
    "uranus": 6,
    "neptune": 7,
    "pluton": 8,
}
ZODIAC_RULERS = {
    "Bélier": ("mars",),
    "Taureau": ("vénus",),
    "Gémeaux": ("mercure",),
    "Cancer": ("lune",),
    "Lion": ("soleil",),
    "Vierge": ("mercure",),
    "Balance": ("vénus",),
    "Scorpion": ("mars", "pluton"),
    "Sagittaire": ("jupiter",),
    "Capricorne": ("saturne",),
    "Verseau": ("uranus",),
    "Poissons": ("neptune",),
}

FULL_TABLE_TOP_POSITIONS = (1, 52, 51)
FULL_TABLE_GRID_POSITIONS = tuple(
    tuple(range(block_end, block_end - 7, -1))
    for block_end in (8, 15, 22, 29, 36, 43, 50)
)
FULL_TABLE_ROW_PLANETS = ("mercure", "vénus", "mars", "jupiter", "saturne", "uranus", "neptune")
FULL_TABLE_COLUMN_PLANETS = ("neptune", "uranus", "saturne", "jupiter", "mars", "vénus", "mercure")


def _as_date(value: date | datetime | str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        # ISO first; then common French notation.
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                pass
    raise TypeError(f"Unsupported date: {value!r}")


def _excel_round(value: float) -> int:
    """Excel ROUND(x, 0): halves away from zero."""
    if value >= 0:
        return math.floor(value + 0.5)
    return math.ceil(value - 0.5)


def _excel_rounddown(value: float) -> int:
    """Excel ROUNDDOWN(x, 0), for positive values used here."""
    return math.floor(value) if value >= 0 else math.ceil(value)


def _excel_quotient(a: int, b: int) -> int:
    # Inputs here are non-negative, matching Excel QUOTIENT.
    return math.trunc(a / b)


def _excel_mod(a: int, b: int) -> int:
    # Excel MOD has the divisor's sign; b is positive here.
    return a % b


def excel_yearfrac_basis0(start: date, end: date) -> float:
    """
    Approximate Excel YEARFRAC(start,end,0), i.e. US NASD 30/360,
    sufficient for the age calculation used by this workbook.

    The workbook immediately applies ROUNDDOWN(...,0), so the integer
    age is the relevant output.
    """
    if end < start:
        return -excel_yearfrac_basis0(end, start)

    d1, d2 = start.day, end.day
    m1, m2 = start.month, end.month
    y1, y2 = start.year, end.year

    # US 30/360 convention, including the standard end-of-February rules.
    import calendar
    last_feb1 = m1 == 2 and d1 == calendar.monthrange(y1, 2)[1]
    last_feb2 = m2 == 2 and d2 == calendar.monthrange(y2, 2)[1]

    if last_feb1:
        d1 = 30
    if last_feb2 and d1 == 30:
        d2 = 30

    if d1 == 31:
        d1 = 30
    if d2 == 31 and d1 == 30:
        d2 = 30

    return ((360 * (y2 - y1)) + 30 * (m2 - m1) + (d2 - d1)) / 360.0


@dataclass(frozen=True)
class TimeState:
    days_elapsed: int
    weeks_elapsed: int
    weekday_position: int  # 1..7
    cycle_90_block: int    # QUOTIENT(weeks,90)
    cycle_90_position: int # 0..89
    cycle_90_series: int   # 1..90
    cycle_start_date: date
    weekday_start_date: date
    age: int
    age_seven_year_block: int
    age_seven_year_series: int
    age_year_series: int       # wrapped internal row, 1..90
    age_year_cycle_number: int # unwrapped sequence number, age + 1


@dataclass(frozen=True)
class CardAtPosition:
    series_id: int
    position_1based: int
    card_number: int
    card_label: str


class OlneyEngine:
    def __init__(self, data_path: str | Path | None = None):
        if data_path is None:
            data_path = Path(__file__).with_name("data.json")
        raw = json.loads(Path(data_path).read_text(encoding="utf-8"))
        self.cards: dict[int, str] = {int(k): v for k, v in raw["cards"].items()}
        self.series: dict[int, list[int]] = {
            int(item["id"]): list(map(int, item["cards"]))
            for item in raw["series"]
        }

        if len(self.series) != 90:
            raise ValueError("Olney data must contain exactly 90 series.")
        for sid, seq in self.series.items():
            if len(seq) != 52:
                raise ValueError(f"Series {sid} must contain 52 cards.")
            if set(seq) != set(range(1, 53)):
                raise ValueError(f"Series {sid} is not a permutation of 1..52.")

    # ---------- Cards / series ----------

    def card_label(self, card_number: int) -> str:
        return self.cards[card_number]

    def get_series(self, series_id: int) -> list[int]:
        if not 1 <= series_id <= 90:
            raise ValueError("series_id must be in 1..90")
        return self.series[series_id].copy()

    def cyclic_series_id(self, cycle_number: int) -> int:
        """Map an unbounded 1-based cycle number onto the 90 stored tables."""
        if cycle_number < 1:
            raise ValueError("cycle_number must be positive")
        return ((cycle_number - 1) % 90) + 1

    def table_name(self, series_id: int, include_prefix: bool = True) -> str:
        """User-facing Olney table name for an internal series row."""
        if not 1 <= series_id <= 90:
            raise ValueError("series_id must be in 1..90")
        if series_id == 1:
            return "Tableau 0.1" if include_prefix else "0.1"
        return f"Tableau {series_id - 1}" if include_prefix else str(series_id - 1)

    def card_at(self, series_id: int, position_1based: int) -> CardAtPosition:
        """
        Cyclic access to the 52-card series.
        This is the semantic equivalent of Feuil2's 10-cell extension.
        """
        seq = self.get_series(series_id)
        idx = (position_1based - 1) % 52
        n = seq[idx]
        return CardAtPosition(series_id, idx + 1, n, self.card_label(n))

    def find_card_position(self, series_id: int, card_number: int) -> int:
        """Return 1-based position of card_number in the canonical 52-card series."""
        seq = self.get_series(series_id)
        try:
            return seq.index(card_number) + 1
        except ValueError:
            raise ValueError(f"Card {card_number} not found in series {series_id}")

    def positional_exchange(self, reference_series_id: int, active_series_id: int,
                            card_number: int) -> dict[str, Any]:
        """Describe how a personal card changes seats between two tables.

        The displacement card is the card whose reference seat is occupied by
        the personal card in the active table.  The environment card is the
        active-table card now occupying the personal card's reference seat.
        """
        reference_position = self.find_card_position(reference_series_id, card_number)
        active_position = self.find_card_position(active_series_id, card_number)
        displacement = self.card_at(reference_series_id, active_position)
        environment = self.card_at(active_series_id, reference_position)
        return {
            "card_number": card_number,
            "card": self.card_label(card_number),
            "reference_series_id": reference_series_id,
            "active_series_id": active_series_id,
            "reference_position": reference_position,
            "active_position": active_position,
            "displacement": {
                "card_number": displacement.card_number,
                "card": displacement.card_label,
                "position": displacement.position_1based,
            },
            "environment": {
                "card_number": environment.card_number,
                "card": environment.card_label,
                "position": environment.position_1based,
            },
        }

    def full_table_layout(self, series_id: int) -> dict[str, Any]:
        """Return the workbook's complete 52-card visual layout."""
        def cell(position: int) -> dict[str, Any]:
            item = self.card_at(series_id, position)
            return {
                "position": position,
                "card_number": item.card_number,
                "card": item.card_label,
            }

        return {
            "series_id": series_id,
            "top": [cell(position) for position in FULL_TABLE_TOP_POSITIONS],
            "grid": [
                [cell(position) for position in row]
                for row in FULL_TABLE_GRID_POSITIONS
            ],
        }

    def table_coordinates(self, position_1based: int) -> dict[str, Optional[str]]:
        """Return the visible row and column attached to a table position."""
        if not 1 <= position_1based <= 52:
            raise ValueError("position_1based must be in 1..52")

        if position_1based in FULL_TABLE_TOP_POSITIONS:
            return {
                "zone": "couronne",
                "row_planet": None,
                "column_planet": None,
            }

        row_index = (position_1based - 2) // 7
        block_end = 8 + row_index * 7
        column_index = block_end - position_1based
        return {
            "zone": "grille",
            "row_planet": FULL_TABLE_ROW_PLANETS[row_index],
            "column_planet": FULL_TABLE_COLUMN_PLANETS[column_index],
        }

    def anniversary_date(self, birth_date: date | datetime | str, age: int) -> date:
        """Return the exact calendar anniversary for an age."""
        birth = _as_date(birth_date)
        if age < 0:
            raise ValueError("age must be non-negative")
        try:
            return birth.replace(year=birth.year + age)
        except ValueError:
            # A 29 February anniversary falls on 28 February in a
            # non-leap destination year.
            return birth.replace(year=birth.year + age, day=28)

    def annual_cycle_boundaries(self, birth_date: date | datetime | str,
                                age: int) -> list[date]:
        """Return 8 continuous boundaries for the 7 annual subcycles."""
        start = self.anniversary_date(birth_date, age)
        end = self.anniversary_date(birth_date, age + 1)
        # The final six periods remain exactly 52 days. The first absorbs
        # the one or two extra calendar days so the cycle opens and closes
        # on the person's exact anniversaries.
        return [start] + [
            end - timedelta(days=52 * remaining)
            for remaining in range(6, 0, -1)
        ] + [end]

    def navigate_date(self, birth_date: date | datetime | str,
                      target_date: date | datetime | str,
                      level: str, direction: int) -> date:
        """Move the analysed date through the life, year, 52-day or day controls."""
        birth = _as_date(birth_date)
        target = _as_date(target_date)
        step = 1 if direction >= 0 else -1

        if level == "life_path":
            current_period = self.age(birth, target) // 13
            destination_period = current_period + step
            if destination_period < 0:
                raise ValueError("Le Chemin de vie commence à la naissance.")
            moved = self.anniversary_date(birth, destination_period * 13)
        elif level == "year":
            current_age = self.age(birth, target)
            destination_age = current_age + step
            if destination_age < 0:
                raise ValueError("La date analysée ne peut pas précéder la naissance.")
            moved = self.anniversary_date(birth, destination_age)
        elif level == "fifty_two_day":
            window = self.fifty_two_day_window(birth, target)
            if step > 0:
                moved = _as_date(window["end"])
            else:
                previous_day = _as_date(window["start"]) - timedelta(days=1)
                previous_window = self.fifty_two_day_window(birth, previous_day)
                moved = _as_date(previous_window["start"])
        elif level == "day":
            moved = target + timedelta(days=step)
        else:
            raise ValueError(
                "level must be 'life_path', 'year', 'fifty_two_day' or 'day'"
            )

        if moved < birth:
            raise ValueError("La date analysée ne peut pas précéder la naissance.")
        return moved

    # ---------- Birth / time ----------

    def birth_card_number(self, birth_date: date | datetime | str) -> int:
        d = _as_date(birth_date)
        return 55 - (d.day + 2 * d.month)

    def birth_card(self, birth_date: date | datetime | str) -> CardAtPosition:
        n = self.birth_card_number(birth_date)
        if n == 0:
            return CardAtPosition(0, 0, 0, "Joker")
        return CardAtPosition(0, 0, n, self.card_label(n))

    def is_joker_birth_date(self, birth_date: date | datetime | str) -> bool:
        return self.birth_card_number(birth_date) == 0

    def hour_card(
        self,
        target_date: date | datetime | str,
        target_time: str,
        target_place: str,
    ) -> dict[str, Any]:
        """Return the independent hour card for the analyzed moment."""
        return calculate_hour_card(_as_date(target_date), target_time, target_place)

    def zodiac_sign(self, birth_date: date | datetime | str) -> str:
        """Return the western zodiac sign name for a birth date."""
        value = _as_date(birth_date)
        month_day = (value.month, value.day)
        signs = (
            ((1, 20), "Verseau"),
            ((2, 19), "Poissons"),
            ((3, 21), "Bélier"),
            ((4, 20), "Taureau"),
            ((5, 21), "Gémeaux"),
            ((6, 21), "Cancer"),
            ((7, 23), "Lion"),
            ((8, 23), "Vierge"),
            ((9, 23), "Balance"),
            ((10, 23), "Scorpion"),
            ((11, 22), "Sagittaire"),
            ((12, 22), "Capricorne"),
        )
        result = "Capricorne"
        for boundary, sign in signs:
            if month_day >= boundary:
                result = sign
            else:
                break
        return result

    def secondary_cards(self, birth_date: date | datetime | str) -> dict[str, Any]:
        """Read sign-ruler cards relative to the birth card in table 0.1."""
        birth = _as_date(birth_date)
        sign = self.zodiac_sign(birth)
        rulers = ZODIAC_RULERS[sign]
        birth_n = self.birth_card_number(birth)
        if birth_n == 0:
            return {"sign": sign, "series_id": 1, "cards": []}

        birth_position = self.find_card_position(1, birth_n)
        cards = []
        for ruler in rulers:
            item = self.card_at(1, birth_position + RULER_OFFSETS[ruler])
            cards.append({
                "ruler": ruler,
                "offset_from_birth_card": RULER_OFFSETS[ruler],
                "card_number": item.card_number,
                "card": item.card_label,
                "position": item.position_1based,
            })
        return {"sign": sign, "series_id": 1, "cards": cards}

    def age(self, birth_date: date | datetime | str, target_date: date | datetime | str) -> int:
        b, t = _as_date(birth_date), _as_date(target_date)
        if t < b:
            raise ValueError("target_date cannot precede birth_date")
        return _excel_rounddown(excel_yearfrac_basis0(b, t))

    def time_state(self, birth_date: date | datetime | str,
                   target_date: date | datetime | str) -> TimeState:
        b, t = _as_date(birth_date), _as_date(target_date)
        if t < b:
            raise ValueError("target_date cannot precede birth_date")

        days = (t - b).days
        weeks = _excel_quotient(days, 7)
        weekday_position = _excel_mod(days, 7) + 1
        cycle_90_block = _excel_quotient(weeks, 90)
        cycle_90_position = _excel_mod(weeks, 90)
        cycle_90_series = cycle_90_position + 1

        cycle_start = t + timedelta(days=(89 - cycle_90_position) * 7)
        weekday_start = cycle_start - timedelta(days=weekday_position - 1)

        a = self.age(b, t)
        year_cycle_number = a + 1

        return TimeState(
            days_elapsed=days,
            weeks_elapsed=weeks,
            weekday_position=weekday_position,
            cycle_90_block=cycle_90_block,
            cycle_90_position=cycle_90_position,
            cycle_90_series=cycle_90_series,
            cycle_start_date=cycle_start,
            weekday_start_date=weekday_start,
            age=a,
            age_seven_year_block=_excel_quotient(a, 7),
            age_seven_year_series=_excel_quotient(a, 7) + 1,
            age_year_series=self.cyclic_series_id(year_cycle_number),
            age_year_cycle_number=year_cycle_number,
        )

    # ---------- Core relative-card reading ----------

    def relative_cards(self, series_id: int, birth_card_number: int) -> dict[str, CardAtPosition]:
        """
        Reproduces the Feuil1 relative reads around the birth card:
          -1 = lune
           0 = soleil
          +1..+7 = planets
          +8 = défi
          +9 = résultat
        """
        pos = self.find_card_position(series_id, birth_card_number)
        result = {}
        for name, offset in OFFSETS.items():
            result[name] = self.card_at(series_id, pos + offset)
        return result

    def _relative_rows(self, series_id: int, birth_card_number: int) -> list[dict[str, Any]]:
        cards = self.relative_cards(series_id, birth_card_number)
        return [
            {
                "slot": name,
                "offset_from_birth_card": OFFSETS[name],
                "card_number": item.card_number,
                "card": item.card_label,
                "position": item.position_1based,
                "series_id": series_id,
            }
            for name, item in cards.items()
        ]

    def life_path_table(self, birth_date: date | datetime | str,
                        target_date: date | datetime | str, *,
                        birth_card_number: int | None = None) -> dict[str, Any]:
        """Return the manifested-order reading and its active 13-year period."""
        b, t = _as_date(birth_date), _as_date(target_date)
        age = self.age(b, t)
        cycle_number = age // 91
        cycle_base_age = cycle_number * 91
        cycle_age = age % 91
        active_index = min(cycle_age // 13, 6)
        active_slot = SEVEN_YEAR_PLANETS[active_index]
        birth_n = int(birth_card_number or self.birth_card_number(b))
        cards = self.relative_cards(1, birth_n)

        rows = []
        for slot, item in cards.items():
            row = {
                "slot": slot,
                "offset_from_birth_card": OFFSETS[slot],
                "card_number": item.card_number,
                "card": item.card_label,
                "position": item.position_1based,
                "series_id": 1,
                "age_start": None,
                "age_end": None,
                "age_range": None,
            }
            if slot in SEVEN_YEAR_PLANETS:
                index = SEVEN_YEAR_PLANETS.index(slot)
                base_start, base_end = LIFE_PATH_AGE_RANGES[index]
                start = cycle_base_age + base_start
                end = cycle_base_age + base_end
                row.update({
                    "age_start": start,
                    "age_end": end,
                    "age_range": f"{start} – {end} ans",
                })
            rows.append(row)

        active = cards[active_slot]
        base_start, base_end = LIFE_PATH_AGE_RANGES[active_index]
        active_start = cycle_base_age + base_start
        active_end = cycle_base_age + base_end
        return {
            "type": "life_path",
            "series_id": 1,
            "age": age,
            "cycle_number": cycle_number,
            "cycle_age": cycle_age,
            "active_slot": active_slot,
            "active_age_start": active_start,
            "active_age_end": active_end,
            "active_age_range": f"{active_start} – {active_end} ans",
            "active_start_date": self.anniversary_date(b, active_start).isoformat(),
            "active_end_date": self.anniversary_date(b, active_end + 1).isoformat(),
            "card_number": active.card_number,
            "card": active.card_label,
            "position": active.position_1based,
            "rows": rows,
        }

    # ---------- 7-year table ----------

    def seven_year_table(self, birth_date: date | datetime | str,
                         target_date: date | datetime | str, *,
                         birth_card_number: int | None = None) -> dict[str, Any]:
        b, t = _as_date(birth_date), _as_date(target_date)
        ts = self.time_state(b, t)
        birth_n = int(birth_card_number or self.birth_card_number(b))
        sid = ts.age_seven_year_series

        rows = []
        base_year = b.year + (sid - 1) * 7
        for i, planet in enumerate(SEVEN_YEAR_PLANETS, start=1):
            card = self.card_at(sid, self.find_card_position(sid, birth_n) + i)
            # Excel E19 = (H6-1)*7 + C19 - 1
            # with C19=1 -> 0; then year = YEAR(birth)+E19.
            year_offset = (sid - 1) * 7 + i - 1
            rows.append({
                "slot": planet,
                "index": i,
                "offset_from_birth_card": i,
                "card_number": card.card_number,
                "card": card.card_label,
                "year": b.year + year_offset,
                "position": card.position_1based,
            })

        extra = self.relative_cards(sid, birth_n)
        rows.extend([
            {
                "slot": "défi",
                "index": 8,
                "offset_from_birth_card": 8,
                "card_number": extra["défi"].card_number,
                "card": extra["défi"].card_label,
                "year": None,
                "position": extra["défi"].position_1based,
            },
            {
                "slot": "résultat",
                "index": 9,
                "offset_from_birth_card": 9,
                "card_number": extra["résultat"].card_number,
                "card": extra["résultat"].card_label,
                "year": None,
                "position": extra["résultat"].position_1based,
            },
        ])
        return {
            "type": "seven_year",
            "series_id": sid,
            "age": ts.age,
            "birth_card": self.card_label(birth_n),
            "rows": rows,
        }

    # ---------- Annual table ----------

    def year_table(self, birth_date: date | datetime | str,
                   target_date: date | datetime | str, *,
                   birth_card_number: int | None = None) -> dict[str, Any]:
        b, t = _as_date(birth_date), _as_date(target_date)
        ts = self.time_state(b, t)
        birth_n = int(birth_card_number or self.birth_card_number(b))
        sid = ts.age_year_series
        pos = self.find_card_position(sid, birth_n)

        rows = []
        boundaries = self.annual_cycle_boundaries(b, ts.age)
        for i, planet in enumerate(SEVEN_YEAR_PLANETS, start=1):
            card = self.card_at(sid, pos + i)
            m_date = boundaries[i - 1]
            n_date = boundaries[i]
            rows.append({
                "slot": planet,
                "index": i,
                "card_number": card.card_number,
                "card": card.card_label,
                "period_start": m_date.isoformat(),
                "period_end": n_date.isoformat(),
                "position": card.position_1based,
            })

        extra = self.relative_cards(sid, birth_n)
        rows.extend([
            {"slot": "défi", "index": 8, "offset_from_birth_card": 8,
             "card_number": extra["défi"].card_number, "card": extra["défi"].card_label,
             "period_start": None, "period_end": None,
             "position": extra["défi"].position_1based},
            {"slot": "résultat", "index": 9, "offset_from_birth_card": 9,
             "card_number": extra["résultat"].card_number, "card": extra["résultat"].card_label,
             "period_start": None, "period_end": None,
             "position": extra["résultat"].position_1based},
        ])

        # Excel G15 = VLOOKUP(B42,E19:F25,2)
        #
        # E19:E25 are generated from the CURRENT 7-year series:
        #   E19 = (H6-1)*7 + 1 - 1
        #   ...
        #   E25 = (H6-1)*7 + 7 - 1
        #
        # Therefore the "carte de l'année" is NOT taken from this annual
        # series (P6). It is taken from the 7-year series (H6), at the
        # relative offset corresponding to the age inside the 7-year cycle.
        #
        # Example: age 37 -> H6=6, age%7=2 -> relative offset +3.
        seven_sid = ts.age_seven_year_series
        seven_pos = self.find_card_position(seven_sid, birth_n)
        year_offset_in_cycle = (ts.age % 7) + 1
        year_card_obj = self.card_at(seven_sid, seven_pos + year_offset_in_cycle)
        year_card = year_card_obj.card_label

        return {
            "type": "year",
            "series_id": sid,
            "age": ts.age,
            "birth_card": self.card_label(birth_n),
            "year_card": year_card,
            "rows": rows,
        }

    # ---------- Week table ----------

    def week_table(self, birth_date: date | datetime | str,
                   target_date: date | datetime | str, *,
                   birth_card_number: int | None = None) -> dict[str, Any]:
        b, t = _as_date(birth_date), _as_date(target_date)
        ts = self.time_state(b, t)
        birth_n = int(birth_card_number or self.birth_card_number(b))
        sid = ts.cycle_90_series
        pos = self.find_card_position(sid, birth_n)

        # Excel T/U columns:
        # U19 = P2 - B37 + S19, with S19=1, so first date is
        # target_date - (weekday_position-1), then +0..+6.
        start = t - timedelta(days=ts.weekday_position - 1)

        rows = []
        for i, planet in enumerate(SEVEN_YEAR_PLANETS, start=1):
            card = self.card_at(sid, pos + i)
            d = start + timedelta(days=i - 1)
            rows.append({
                "slot": planet,
                "index": i,
                "date": d.isoformat(),
                "card_number": card.card_number,
                "card": card.card_label,
                "position": card.position_1based,
            })

        extra = self.relative_cards(sid, birth_n)
        rows.extend([
            {"slot": "défi", "index": 8, "date": None,
             "card_number": extra["défi"].card_number, "card": extra["défi"].card_label,
             "position": extra["défi"].position_1based},
            {"slot": "résultat", "index": 9, "date": None,
             "card_number": extra["résultat"].card_number, "card": extra["résultat"].card_label,
             "position": extra["résultat"].position_1based},
        ])

        # Excel P2 against U19:U25 with approximate VLOOKUP.
        # U19..U25 are 7 consecutive dates starting at week start.
        day_index = (t - start).days
        day_card = rows[day_index]["card"]

        return {
            "type": "week",
            "series_id": sid,
            "cycle_90_position": ts.cycle_90_position,
            "week_start": start.isoformat(),
            "week_end": (start + timedelta(days=6)).isoformat(),
            "rows": rows,
            "day_card": day_card,
        }

    # ---------- 52-day table / card ----------

    def fifty_two_day_window(self, birth_date: date | datetime | str,
                             target_date: date | datetime | str) -> dict[str, Any]:
        b, t = _as_date(birth_date), _as_date(target_date)
        ts = self.time_state(b, t)

        cycle_age = ts.age
        boundaries = self.annual_cycle_boundaries(b, cycle_age)
        if t < boundaries[0] and cycle_age > 0:
            cycle_age -= 1
            boundaries = self.annual_cycle_boundaries(b, cycle_age)

        q = next(
            (
                index for index in range(7)
                if boundaries[index] <= t < boundaries[index + 1]
            ),
            6,
        )
        lower = boundaries[q]
        upper = boundaries[q + 1]
        elapsed = (t - boundaries[0]).days

        return {
            "anchor_date": boundaries[0].isoformat(),
            "next_annual_anchor": boundaries[-1].isoformat(),
            "cycle_age": cycle_age,
            "offset_days": elapsed,
            "window_index": q,
            "start": lower.isoformat(),
            "end": upper.isoformat(),
            "next_boundary": upper.isoformat(),
        }

    def fifty_two_day_table(self, birth_date: date | datetime | str,
                            target_date: date | datetime | str, *,
                            birth_card_number: int | None = None) -> dict[str, Any]:
        b, t = _as_date(birth_date), _as_date(target_date)
        birth_n = int(birth_card_number or self.birth_card_number(b))

        window = self.fifty_two_day_window(b, t)

        # The workbook's 52-day card is selected from N19:N25 by
        # approximate VLOOKUP(B47,...), where the card values are the
        # same relative-card rows used in the annual block.
        sid = self.cyclic_series_id(int(window["cycle_age"]) + 1)
        rel = self.relative_cards(sid, birth_n)

        planet = SEVEN_YEAR_PLANETS[int(window["window_index"])]
        selected = rel[planet]

        return {
            "type": "52_day",
            "series_id": sid,
            "window": window,
            "selected_slot": planet,
            "card_number": selected.card_number,
            "card": selected.card_label,
            "position": selected.position_1based,
        }

    # ---------- Day card ----------

    def day_table(self, birth_date: date | datetime | str,
                  target_date: date | datetime | str, *,
                  birth_card_number: int | None = None) -> dict[str, Any]:
        b, t = _as_date(birth_date), _as_date(target_date)
        ts = self.time_state(b, t)
        birth_n = int(birth_card_number or self.birth_card_number(b))
        sid = ts.cycle_90_series
        pos = self.find_card_position(sid, birth_n)

        start = t - timedelta(days=ts.weekday_position - 1)

        rows = []
        for i, planet in enumerate(SEVEN_YEAR_PLANETS, start=1):
            card = self.card_at(sid, pos + i)
            d = start + timedelta(days=i - 1)
            rows.append({
                "slot": planet,
                "index": i,
                "date": d.isoformat(),
                "card_number": card.card_number,
                "card": card.card_label,
                "position": card.position_1based,
            })

        day_card = rows[ts.weekday_position - 1]["card"]
        day_number = rows[ts.weekday_position - 1]["card_number"]

        return {
            "type": "day",
            "series_id": sid,
            "date": t.isoformat(),
            "week_start": start.isoformat(),
            "weekday_position": ts.weekday_position,
            "card_number": day_number,
            "card": day_card,
            "rows": rows,
        }

    # ---------- Master state ----------

    def full_state(
        self,
        birth_date: date | datetime | str,
        target_date: date | datetime | str,
        target_time: str | None = None,
        target_place: str | None = None,
        *,
        birth_card_number: int | None = None,
    ) -> dict[str, Any]:
        b, t = _as_date(birth_date), _as_date(target_date)
        ts = self.time_state(b, t)
        if birth_card_number is None:
            birth = self.birth_card(b)
        else:
            number = int(birth_card_number)
            if not 1 <= number <= 52:
                raise ValueError("birth_card_number must be in 1..52")
            birth = CardAtPosition(0, 0, number, self.card_label(number))
        if (target_time is None) != (target_place is None):
            raise ValueError(
                "L'heure et le lieu analysés doivent être fournis ensemble."
            )
        hour_card = (
            self.hour_card(t, target_time, target_place)
            if target_time is not None and target_place is not None
            else None
        )

        if birth.card_number == 0:
            return {
                "engine_version": "1.8.7",
                "birth_date": b.isoformat(),
                "target_date": t.isoformat(),
                "birth_card_override": birth_card_number is not None,
                "joker": True,
                "birth": {
                    "card_number": 0,
                    "card": "Joker",
                },
                "time": asdict(ts),
                "life_path": None,
                "secondary_cards": self.secondary_cards(b),
                "seven_year": None,
                "year": None,
                "week": None,
                "fifty_two_day": None,
                "day": None,
                "hour_card": hour_card,
            }

        return {
            "engine_version": "1.8.7",
            "birth_date": b.isoformat(),
            "target_date": t.isoformat(),
            "birth_card_override": birth_card_number is not None,
            "joker": False,
            "birth": {
                "card_number": birth.card_number,
                "card": birth.card_label,
            },
            "time": asdict(ts),
            "life_path": self.life_path_table(
                b, t, birth_card_number=birth.card_number
            ),
            "secondary_cards": (
                {"sign": None, "series_id": 1, "cards": [], "virtual": True}
                if birth_card_number is not None else self.secondary_cards(b)
            ),
            "seven_year": self.seven_year_table(
                b, t, birth_card_number=birth.card_number
            ),
            "year": self.year_table(b, t, birth_card_number=birth.card_number),
            "week": self.week_table(b, t, birth_card_number=birth.card_number),
            "fifty_two_day": self.fifty_two_day_table(
                b, t, birth_card_number=birth.card_number
            ),
            "day": self.day_table(b, t, birth_card_number=birth.card_number),
            "hour_card": hour_card,
        }

    # ---------- AI-facing helpers ----------

    def tool_get_state(
        self,
        birth_date: str,
        target_date: str,
        target_time: str | None = None,
        target_place: str | None = None,
    ) -> dict[str, Any]:
        """Safe JSON-ready tool entry point for Olney's backend."""
        return self.full_state(birth_date, target_date, target_time, target_place)

    def tool_compare_dates(self, birth_date: str,
                           date_a: str, date_b: str) -> dict[str, Any]:
        a = self.full_state(birth_date, date_a)
        b = self.full_state(birth_date, date_b)
        return {
            "birth_date": _as_date(birth_date).isoformat(),
            "date_a": a,
            "date_b": b,
        }

    def tool_get_interpretation_context(
        self,
        birth_date: str,
        target_date: str,
        target_time: str | None = None,
        target_place: str | None = None,
        profile_history: list[dict[str, Any]] | None = None,
        *,
        reading_focus: str = "general",
        profile_id: str | None = None,
        reading_mode: str = "current",
        reading_material: dict[str, Any] | None = None,
        reading_options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return calculated facts enriched for Olney's UI and future LLM.

        The import stays local so the deterministic calculation layer remains
        usable on its own.  No interpretation rule is involved in calculating
        cards, dates, tables or positions.
        """
        from interpretation_runtime import InterpretationContextBuilder

        return InterpretationContextBuilder(self).from_dates(
            birth_date,
            target_date,
            target_time,
            target_place,
            profile_history=profile_history,
            reading_focus=reading_focus,
            profile_id=profile_id,
            reading_mode=reading_mode,
            reading_material=reading_material,
            reading_options=reading_options,
        )


if __name__ == "__main__":
    engine = OlneyEngine()
    state = engine.full_state("1965-05-18", "2025-02-20")
    print(json.dumps(state, ensure_ascii=False, indent=2, default=str))
