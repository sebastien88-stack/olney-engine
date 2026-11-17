from threading import Event, get_ident
from time import monotonic, sleep

from ui_jobs import BusyIndicator, DeferredView, LatestJobs


class Scheduler:
    def __init__(self):
        self.calls = {}
        self.serial = 0
        self.now = 0

    def after(self, delay, callback):
        self.serial += 1
        self.calls[self.serial] = (self.now + delay, callback)
        return self.serial

    def after_cancel(self, token):
        self.calls.pop(token, None)

    def advance(self, delta):
        self.now += delta
        due = [(key, callback) for key, (when, callback) in self.calls.items() if when <= self.now]
        for key, callback in due:
            if self.calls.pop(key, None) is not None:
                callback()


def drain(scheduler, jobs):
    deadline = monotonic() + 5
    while jobs.busy():
        scheduler.advance(25)
        assert monotonic() < deadline
        sleep(0.001)


def test_background_jobs_keep_only_latest_request_and_callbacks_on_main_thread():
    scheduler, gate, started = Scheduler(), Event(), Event()
    jobs = LatestJobs(scheduler)
    outputs, ran = [], []
    main = get_ident()

    def slow():
        ran.append(get_ident())
        started.set()
        assert gate.wait(5)
        return "obsolete"

    try:
        jobs.submit("analysis", slow, outputs.append, outputs.append)
        assert started.wait(2)
        jobs.submit("analysis", lambda: ran.append("skipped"), outputs.append, outputs.append)
        jobs.submit("analysis", lambda: "latest", lambda value: outputs.append((value, get_ident())), outputs.append)
        gate.set()
        drain(scheduler, jobs)
        assert outputs == [("latest", main)]
        assert len(ran) == 1 and ran[0] != main
    finally:
        gate.set()
        jobs.close()


def test_cancelled_errors_never_reach_ui_and_new_jobs_still_work():
    scheduler, gate, started = Scheduler(), Event(), Event()
    jobs, outputs = LatestJobs(scheduler), []

    def broken():
        started.set()
        assert gate.wait(5)
        raise ValueError("obsolete failure")

    try:
        jobs.submit("timeline", broken, outputs.append, outputs.append)
        assert started.wait(2)
        jobs.cancel()
        assert not jobs.busy()
        jobs.submit("analysis", lambda: "ok", outputs.append, outputs.append)
        gate.set()
        drain(scheduler, jobs)
        assert outputs == ["ok"]
    finally:
        gate.set()
        jobs.close()


def test_current_error_stops_busy_state_and_shutdown_cancels_poll():
    scheduler, outputs = Scheduler(), []
    jobs = LatestJobs(scheduler)
    def fail():
        raise ValueError("expected")
    jobs.submit("analysis", fail, outputs.append, outputs.append)
    drain(scheduler, jobs)
    assert len(outputs) == 1 and isinstance(outputs[0], ValueError)
    assert not jobs.busy()
    jobs.close()
    assert not scheduler.calls
    jobs.submit("analysis", lambda: 1, outputs.append, outputs.append)
    assert not jobs.busy()


def test_busy_indicator_delays_animates_and_clears_without_flashing():
    scheduler, labels = Scheduler(), []
    indicator = BusyIndicator(scheduler, labels.append)
    indicator.set_busy(True)
    scheduler.advance(149)
    assert labels == []
    indicator.set_busy(False)
    scheduler.advance(1000)
    assert labels == [""]
    indicator.set_busy(True)
    scheduler.advance(150)
    assert "Mise à jour" in labels[-1]
    frame = labels[-1]
    scheduler.advance(100)
    assert frame != labels[-1]
    indicator.set_busy(False)
    assert labels[-1] == "" and not scheduler.calls


class View:
    def __init__(self):
        self.calls = []
    def update(self, value):
        self.calls.append(("data", value))
    def show_message(self, value):
        self.calls.append(("message", value))
    def apply_theme(self):
        self.calls.append(("theme", None))


def test_hidden_views_coalesce_updates_and_theme_in_one_render_on_open():
    view, visible = View(), [False]
    deferred = DeferredView(view, lambda: visible[0])
    deferred.update({"value": 1})
    deferred.update({"value": 2})
    deferred.apply_theme()
    assert not view.calls
    visible[0] = True
    deferred.flush()
    assert view.calls == [("data", {"value": 2})]
    deferred.update({"value": 2})
    assert deferred.render_count == 1
    deferred.apply_theme()
    assert view.calls[-1] == ("theme", None)


def test_return_to_already_rendered_data_drops_obsolete_pending_payload():
    view, visible = View(), [True]
    deferred = DeferredView(view, lambda: visible[0])
    deferred.update("current")
    visible[0] = False
    deferred.update("superseded")
    deferred.update("current")
    visible[0] = True
    deferred.flush()
    assert view.calls == [("data", "current")]


def test_background_analysis_matches_engine_and_reuses_natal_ascendant():
    from datetime import date
    from analysis_work import AnalysisWork
    from interpretation_runtime import InterpretationKnowledge
    work = AnalysisWork(InterpretationKnowledge.load())
    args = (date(1988, 10, 27), date(2026, 8, 26), "07:51", "Longjumeau, FR",
            "17:51", "Longjumeau, FR", None)
    result = work.analysis(*args)
    expected = work.engine.full_state(args[0], args[1])
    expected["hour_card"] = work.engine.hour_card(args[1], args[4], args[5])
    assert result["state"] == expected
    assert result["context"] == work.builder.from_state(expected, profile_id=None)
    hits = work.ascendant.cache_info().hits
    work.analysis(*args)
    assert work.ascendant.cache_info().hits == hits + 1
