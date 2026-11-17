"""Latest-request-wins work queue. Workers never call Tk or access the user DB."""

from queue import Empty, Queue
from threading import Lock, Thread


class LatestJobs:
    def __init__(self, scheduler, on_change=None):
        self.scheduler = scheduler
        self.on_change = on_change or (lambda: None)
        self._work = Queue()
        self._done = Queue()
        self._lock = Lock()
        self._serial = 0
        self._active = {}
        self._closed = False
        self._poll_id = scheduler.after(20, self._poll)
        Thread(target=self._run, name="olney-calculations", daemon=True).start()

    def submit(self, key, compute, success, failure):
        with self._lock:
            if self._closed:
                return
            self._serial += 1
            token = self._serial
            self._active[key] = (token, success, failure)
        self._work.put((key, token, compute))
        self.on_change()

    def busy(self, key=None):
        with self._lock:
            return bool(self._active) if key is None else key in self._active

    def cancel(self, key=None):
        with self._lock:
            if key is None:
                self._active.clear()
            else:
                self._active.pop(key, None)
        self.on_change()

    def _current(self, key, token):
        with self._lock:
            return not self._closed and self._active.get(key, (None,))[0] == token

    def _run(self):
        while True:
            item = self._work.get()
            if item is None:
                return
            key, token, compute = item
            if not self._current(key, token):
                continue
            try:
                result = compute()
                self._done.put((key, token, result, None))
            except Exception as error:
                self._done.put((key, token, None, error))

    def _poll(self):
        if self._closed:
            return
        try:
            while True:
                try:
                    key, token, result, error = self._done.get_nowait()
                except Empty:
                    break
                if not self._current(key, token):
                    continue
                with self._lock:
                    _, success, failure = self._active.pop(key)
                if error is not None:
                    self.on_change()  # Stop the spinner before a modal error dialog.
                try:
                    (failure if error is not None else success)(error if error is not None else result)
                finally:
                    self.on_change()
        finally:
            if not self._closed:
                self._poll_id = self.scheduler.after(20, self._poll)

    def close(self):
        with self._lock:
            self._closed = True
            self._active.clear()
        self.scheduler.after_cancel(self._poll_id)
        self._work.put(None)


class BusyIndicator:
    """Delayed text animation: no flicker for calculations shorter than 150 ms."""
    def __init__(self, scheduler, set_text, delay=150):
        self.scheduler, self.set_text, self.delay = scheduler, set_text, delay
        self._job = None
        self._active = False
        self._frame = 0

    def set_busy(self, busy):
        if busy == self._active:
            return
        self._active = busy
        if self._job is not None:
            self.scheduler.after_cancel(self._job)
            self._job = None
        if busy:
            self._job = self.scheduler.after(self.delay, self._tick)
        else:
            self.set_text("")

    def _tick(self):
        self.set_text(("◐", "◓", "◑", "◒")[self._frame % 4] + " Mise à jour…")
        self._frame += 1
        self._job = self.scheduler.after(100, self._tick)


class DeferredView:
    """Keep the last displayed view; render the newest payload only when opened."""
    def __init__(self, view, visible):
        self.view = view
        self.visible = visible
        view.is_currently_visible = visible
        self.pending = None
        self.last = None
        self.theme_dirty = False
        self.render_count = 0

    def __getattr__(self, name):
        return getattr(self.view, name)

    def __setattr__(self, name, value):
        if name in {"view", "visible", "pending", "last", "theme_dirty", "render_count"}:
            object.__setattr__(self, name, value)
        else:
            setattr(self.view, name, value)

    def update(self, *args, **kwargs):
        self._stage("update", args, kwargs)

    def show_message(self, *args, **kwargs):
        self._stage("show_message", args, kwargs)

    def show_global_return(self):
        self.view.return_visible = True
        self.apply_theme()

    def hide_global_return(self):
        self.view.return_visible = False
        self.theme_dirty = True

    def _stage(self, method, args, kwargs):
        payload = (method, args, kwargs)
        self.pending = payload if payload != self.last else None
        self.flush()

    def apply_theme(self):
        self.theme_dirty = True
        self.flush()

    def flush(self):
        if not self.visible():
            return
        if self.pending is not None:
            method, args, kwargs = self.pending
            self.last, self.pending = self.pending, None
            getattr(self.view, method)(*args, **kwargs)
            self.render_count += 1
            # Views construct their contents with the current palette.
            self.theme_dirty = False
        elif self.theme_dirty:
            self.view.apply_theme()
            self.theme_dirty = False
