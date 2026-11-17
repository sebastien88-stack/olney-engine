"""Scrollable, wrapped alternative to a Tk listbox for long labels."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class WrappedList(tk.Frame):
    """A small Listbox-compatible widget whose rows can span several lines."""

    def __init__(self, parent, *, width=300, font=("Segoe UI", 10),
                 exportselection=False, borderwidth=0, highlightthickness=1,
                 activestyle="none", **kwargs):
        del exportselection, activestyle
        background = kwargs.pop("background", "white")
        highlight = kwargs.pop("highlightbackground", background)
        super().__init__(
            parent, width=width, borderwidth=borderwidth,
            highlightthickness=highlightthickness,
            highlightbackground=highlight, background=background, **kwargs,
        )
        self._font = font
        self._background = background
        self._foreground = "black"
        self._selectbackground = "#DCE8F2"
        self._selectforeground = "black"
        self._separator = highlight
        self._selected = None
        self._items = []

        self._canvas = tk.Canvas(
            self, width=width, borderwidth=0, highlightthickness=0,
            background=background,
        )
        self._scrollbar = ttk.Scrollbar(
            self, orient="vertical", command=self._canvas.yview,
        )
        self._canvas.configure(yscrollcommand=self._scrollbar.set)
        self._canvas.pack(side="left", fill="both", expand=True)
        self._scrollbar.pack(side="right", fill="y")

        self._content = tk.Frame(self._canvas, background=background)
        self._window = self._canvas.create_window(
            (0, 0), window=self._content, anchor="nw",
        )
        self._content.bind("<Configure>", self._sync_scrollregion)
        self._canvas.bind("<Configure>", self._resize_content)
        self._bind_mousewheel(self._canvas)
        self._bind_mousewheel(self._content)

    def _bind_mousewheel(self, widget):
        widget.bind("<MouseWheel>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        delta = int(event.delta / 120) if event.delta else 0
        if delta:
            self._canvas.yview_scroll(-delta, "units")
        return "break"

    def _sync_scrollregion(self, _event=None):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _resize_content(self, event):
        width = max(80, event.width)
        self._canvas.itemconfigure(self._window, width=width)
        for item in self._items:
            item["label"].configure(wraplength=max(60, width - 24))

    @staticmethod
    def _coerce_index(index, size, *, for_insert=False):
        if index == "end":
            return size if for_insert else max(0, size - 1)
        return max(0, min(int(index), size if for_insert else max(0, size - 1)))

    def insert(self, index, text):
        position = self._coerce_index(index, len(self._items), for_insert=True)
        shell = tk.Frame(self._content, background=self._background)
        label = tk.Label(
            shell, text=str(text), anchor="w", justify="left",
            padx=10, pady=9, font=self._font,
            background=self._background, foreground=self._foreground,
        )
        separator = tk.Frame(shell, height=1, background=self._separator)
        label.pack(fill="both", expand=True)
        separator.pack(fill="x", side="bottom")
        item = {
            "shell": shell, "label": label, "separator": separator,
            "background": self._background, "foreground": self._foreground,
        }
        self._items.insert(position, item)
        self._repack_items()
        for widget in (shell, label, separator):
            widget.bind(
                "<Button-1>",
                lambda _event, current=item: self._select_item(current),
            )
            self._bind_mousewheel(widget)
        self.after_idle(self._sync_scrollregion)

    def _repack_items(self):
        for item in self._items:
            item["shell"].pack_forget()
            item["shell"].pack(fill="x")

    def _select_item(self, item):
        try:
            index = self._items.index(item)
        except ValueError:
            return
        self.selection_set(index)
        self.event_generate("<<ListboxSelect>>")

    def delete(self, first, last=None):
        if not self._items:
            return
        start = self._coerce_index(first, len(self._items))
        stop = self._coerce_index(last if last is not None else first, len(self._items))
        if stop < start:
            start, stop = stop, start
        removed = self._items[start:stop + 1]
        for item in removed:
            item["shell"].destroy()
        del self._items[start:stop + 1]
        if self._selected is not None:
            if start <= self._selected <= stop:
                self._selected = None
            elif self._selected > stop:
                self._selected -= len(removed)
        self.after_idle(self._sync_scrollregion)

    def selection_clear(self, first=0, last="end"):
        if self._selected is None or not self._items:
            return
        start = self._coerce_index(first, len(self._items))
        stop = self._coerce_index(last, len(self._items))
        if start <= self._selected <= stop:
            previous = self._selected
            self._selected = None
            self._paint_item(previous)

    def selection_set(self, index):
        if not self._items:
            return
        selected = self._coerce_index(index, len(self._items))
        previous = self._selected
        self._selected = selected
        if previous is not None and previous != selected:
            self._paint_item(previous)
        self._paint_item(selected)

    def curselection(self):
        return () if self._selected is None else (self._selected,)

    def see(self, index):
        if not self._items:
            return
        selected = self._coerce_index(index, len(self._items))
        self.update_idletasks()
        item = self._items[selected]["shell"]
        total = max(1, self._content.winfo_height())
        viewport = max(1, self._canvas.winfo_height())
        top = item.winfo_y()
        bottom = top + item.winfo_height()
        current_top = self._canvas.canvasy(0)
        current_bottom = current_top + viewport
        if top < current_top:
            self._canvas.yview_moveto(top / total)
        elif bottom > current_bottom:
            self._canvas.yview_moveto(max(0, (bottom - viewport) / total))

    def itemconfigure(self, index, **kwargs):
        if not self._items:
            return
        item = self._items[self._coerce_index(index, len(self._items))]
        if "background" in kwargs:
            item["background"] = kwargs["background"]
        if "foreground" in kwargs:
            item["foreground"] = kwargs["foreground"]
        self._paint_item(self._items.index(item))

    itemconfig = itemconfigure

    def _paint_item(self, index):
        if not 0 <= index < len(self._items):
            return
        item = self._items[index]
        selected = index == self._selected
        background = self._selectbackground if selected else item["background"]
        foreground = self._selectforeground if selected else item["foreground"]
        item["shell"].configure(background=background)
        item["label"].configure(background=background, foreground=foreground)
        item["separator"].configure(background=self._separator)

    def configure(self, cnf=None, **kwargs):
        options = dict(cnf or {})
        options.update(kwargs)
        if "background" in options:
            self._background = options.pop("background")
        if "foreground" in options:
            self._foreground = options.pop("foreground")
        if "selectbackground" in options:
            self._selectbackground = options.pop("selectbackground")
        if "selectforeground" in options:
            self._selectforeground = options.pop("selectforeground")
        if "highlightbackground" in options:
            self._separator = options["highlightbackground"]
        if "highlightcolor" in options:
            options.pop("highlightcolor")
        super().configure(background=self._background, **options)
        if hasattr(self, "_canvas"):
            self._canvas.configure(background=self._background)
            self._content.configure(background=self._background)
            for index, item in enumerate(self._items):
                if item["background"] != self._selectbackground:
                    item["background"] = self._background
                item["foreground"] = self._foreground
                self._paint_item(index)

    config = configure
