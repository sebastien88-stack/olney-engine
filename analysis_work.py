"""UI-independent computations, serialized by ui_jobs; no Tk and no persistence."""
from datetime import timedelta
from functools import lru_cache

from astro_engine import calculate_ascendant, parse_birth_time
from olney_engine import OlneyEngine
from interpretation_runtime import InterpretationContextBuilder
from timeline_runtime import TimelineEngine


class AnalysisWork:
    def __init__(self, knowledge):
        # Initialized lazily on the worker thread, independent of the UI engine.
        self.knowledge = knowledge
        self.engine = None

    def _initialize(self):
        if self.engine is None:
            self.engine = OlneyEngine()
            self.builder = InterpretationContextBuilder(self.engine, self.knowledge)
            self.timeline = TimelineEngine(self.engine)

    @lru_cache(maxsize=32)
    def ascendant(self, birth, time_text, place):
        if not time_text or not place:
            return "—", None
        try:
            return calculate_ascendant(birth, time_text, place)["display_sign"], None
        except ValueError as error:
            return "À vérifier", str(error)

    def analysis(self, birth, target, birth_time, birth_place, analyzed_time, place,
                 profile_id, reading_material=None, birth_card_number=None):
        self._initialize()
        # Validate time before producing a partial dashboard.
        clock_time = parse_birth_time(analyzed_time)
        hour, hour_error = None, None
        try:
            hour = self.engine.hour_card(target, analyzed_time, place)
        except ValueError as error:
            hour_error = str(error)
        state = self.engine.full_state(
            birth, target, birth_card_number=birth_card_number
        )
        state["hour_card"] = hour
        if birth_card_number is None:
            ascendant, ascendant_error = self.ascendant(birth, birth_time, birth_place)
        else:
            # An explicit non-natal reference has no astrological ascendant.
            ascendant, ascendant_error = "—", None
        return {
            "state": state,
            "context": self.builder.from_state(state, profile_id=profile_id, reading_material=reading_material),
            "reading_material": reading_material,
            "ascendant": ascendant, "ascendant_error": ascendant_error,
            "hour_error": hour_error, "clock_time": clock_time,
        }

    def cycle(self, state, profile_id, focus, reading_material=None):
        self._initialize()
        return self.builder.from_state(
            state, profile_id=profile_id, reading_focus=focus, reading_mode="cycle", reading_material=reading_material,
        )

    def periods(self, birth, start, end, levels, place, birth_card_number=None):
        self._initialize()
        until = (end + timedelta(days=1)).date()
        periods = self.timeline.get_periods(
            birth, start.date(), until,
            levels=tuple(x for x in levels if x != "hour"),
            birth_card_number=birth_card_number,
        )
        if "hour" in levels and place:
            periods.extend(self.timeline.get_hour_periods(start, end, place))
        convergences = self.timeline.find_convergences(
            birth, start.date(), until,
            tuple(x for x in levels if x not in ("hour", "life_path")),
            birth_card_number,
        ) if "annual" in levels and "fifty_two_day" in levels else []
        return periods, convergences
