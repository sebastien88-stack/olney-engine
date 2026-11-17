"""Tk interface for Emmett, the local Olney Engine conversation laboratory."""

from __future__ import annotations

from datetime import date, datetime
import json
import tkinter as tk
from brand_theme import LIGHT
from tkinter import messagebox, ttk

from olney_chat import ANGLE_OPTIONS, DEFAULT_MODEL, OPENROUTER_MODEL
from wrapped_list import WrappedList


class OlneyChatView(ttk.Frame):
    """Full-page chat whose messages stay local and whose calls remain stateless."""

    def __init__(self, parent, *, store, service, client, jobs,
                 dark_mode_getter, moment_getter, on_return,
                 initial_subject_key=None):
        super().__init__(parent, padding=(10, 9, 10, 5))
        self._olney_owns_theme = True
        self.store = store
        self.service = service
        self.client = client
        self.jobs = jobs
        self.dark_mode_getter = dark_mode_getter
        self.moment_getter = moment_getter
        self.on_return = on_return
        self.current_thread_id = None
        self.thread_rows = []
        self.subjects = []
        self.subject_by_label = {}
        self.last_context = None
        self.context_visible = False
        self.waiting = False

        self.subject_var = tk.StringVar()
        self.angle_var = tk.StringVar(value=ANGLE_OPTIONS[0])
        self.focus_var = tk.StringVar()
        self.status_var = tk.StringVar()
        self.connection_var = tk.StringVar()

        self._build()
        self.refresh_subjects(initial_subject_key)
        self.refresh_threads()
        self.new_thread(preserve_subject=True)
        self.apply_theme()

    def _build(self):
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 9))
        title = ttk.Frame(header)
        title.pack(side="left", fill="x", expand=True)
        ttk.Label(title, text="EMMETT", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(
            title,
            text="Ton interlocuteur, relié aux calculs de l’Olney Engine et à ton histoire.",
            style="InputLabel.TLabel",
        ).pack(anchor="w", pady=(2, 0))
        ttk.Button(
            header, text="← RETOUR À L’HORLOGE", command=self.on_return
        ).pack(side="right")
        ttk.Button(
            header, text="CONNEXION", command=self.open_connection
        ).pack(side="right", padx=(0, 6))
        self.context_button = ttk.Button(
            header, text="VOIR LE CONTEXTE", command=self.toggle_context
        )
        self.context_button.pack(side="right", padx=(0, 6))

        body = ttk.Panedwindow(self, orient="horizontal")
        body.pack(fill="both", expand=True)
        sidebar = ttk.Frame(body, width=325, padding=(0, 0, 8, 0))
        conversation = ttk.Frame(body)
        body.add(sidebar, weight=0)
        body.add(conversation, weight=1)

        sidebar_head = ttk.Frame(sidebar)
        sidebar_head.pack(fill="x", pady=(0, 7))
        ttk.Label(
            sidebar_head, text="CONVERSATIONS", style="InputLabel.TLabel"
        ).pack(side="left")
        ttk.Button(
            sidebar_head, text="＋ NOUVELLE", command=self.new_thread
        ).pack(side="right")
        self.thread_list = WrappedList(
            sidebar, exportselection=False, borderwidth=0, highlightthickness=1,
            activestyle="none", font=("Segoe UI", 10), width=315,
        )
        self.thread_list.pack(fill="both", expand=True)
        self.thread_list.bind("<<ListboxSelect>>", self._select_thread)
        self.delete_button = ttk.Button(
            sidebar, text="SUPPRIMER", command=self.delete_thread, state="disabled"
        )
        self.delete_button.pack(fill="x", pady=(7, 0))

        controls = ttk.Frame(conversation)
        controls.pack(fill="x", pady=(0, 8))
        controls.columnconfigure(0, weight=3)
        controls.columnconfigure(1, weight=2)
        ttk.Label(controls, text="SUJET", style="InputLabel.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(controls, text="ANGLE DE LECTURE", style="InputLabel.TLabel").grid(
            row=0, column=1, sticky="w", padx=(8, 0)
        )
        self.subject_box = ttk.Combobox(
            controls, textvariable=self.subject_var, state="readonly",
            font=("Segoe UI", 10),
        )
        self.subject_box.grid(row=1, column=0, sticky="ew", pady=(3, 0))
        self.angle_box = ttk.Combobox(
            controls, textvariable=self.angle_var, state="readonly",
            values=ANGLE_OPTIONS, font=("Segoe UI", 10),
        )
        self.angle_box.grid(
            row=1, column=1, sticky="ew", padx=(8, 0), pady=(3, 0)
        )
        ttk.Label(
            controls, textvariable=self.focus_var, style="InputLabel.TLabel"
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(5, 0))
        self.subject_box.bind("<<ComboboxSelected>>", self._subject_changed)
        self.angle_box.bind("<<ComboboxSelected>>", self._angle_changed)

        self.message_shell = tk.Frame(conversation, highlightthickness=1)
        self.message_shell.pack(fill="both", expand=True)
        self.message_shell.grid_rowconfigure(0, weight=1)
        self.message_shell.grid_columnconfigure(0, weight=1)
        self.messages = tk.Text(
            self.message_shell, wrap="word", state="disabled", borderwidth=0,
            highlightthickness=0, padx=24, pady=18, spacing1=3, spacing3=8,
            font=("Segoe UI", 11), cursor="arrow", height=6,
        )
        message_scroll = ttk.Scrollbar(
            self.message_shell, orient="vertical", command=self.messages.yview
        )
        self.messages.configure(yscrollcommand=message_scroll.set)
        self.messages.grid(row=0, column=0, sticky="nsew")
        message_scroll.grid(row=0, column=1, sticky="ns")

        self.context_shell = tk.Frame(conversation, highlightthickness=1)
        self.context_shell.grid_columnconfigure(0, weight=1)
        self.context_shell.grid_rowconfigure(1, weight=1)
        self.context_title = tk.Label(
            self.context_shell, text="CONTEXTE CALCULÉ ENVOYÉ AU MODÈLE",
            anchor="w", padx=12, pady=7, font=("Segoe UI", 9, "bold"),
        )
        self.context_title.grid(row=0, column=0, sticky="ew")
        self.context_text = tk.Text(
            self.context_shell, wrap="none", state="disabled", height=6,
            borderwidth=0, highlightthickness=0, padx=10, pady=8,
            font=("Consolas", 9),
        )
        context_scroll_y = ttk.Scrollbar(
            self.context_shell, orient="vertical", command=self.context_text.yview
        )
        context_scroll_x = ttk.Scrollbar(
            self.context_shell, orient="horizontal", command=self.context_text.xview
        )
        self.context_text.configure(
            yscrollcommand=context_scroll_y.set, xscrollcommand=context_scroll_x.set
        )
        self.context_text.grid(row=1, column=0, sticky="nsew")
        context_scroll_y.grid(row=1, column=1, sticky="ns")
        context_scroll_x.grid(row=2, column=0, sticky="ew")

        composer = ttk.Frame(conversation)
        composer.pack(fill="x", pady=(8, 0))
        composer.columnconfigure(0, weight=1)
        ttk.Label(
            composer, text="ÉCRIS TON MESSAGE", style="InputLabel.TLabel"
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))
        self.input = tk.Text(
            composer, wrap="word", height=3, borderwidth=0,
            highlightthickness=2, padx=10, pady=8, font=("Segoe UI", 11),
        )
        self.input.grid(row=1, column=0, sticky="ew")
        self.send_button = ttk.Button(
            composer, text="ENVOYER  ›", style="Calculate.TButton",
            command=self.send,
        )
        self.send_button.grid(row=1, column=1, sticky="nsew", padx=(8, 0))
        self.input.bind("<Return>", self._send_shortcut)

        status = ttk.Frame(conversation)
        status.pack(fill="x", pady=(6, 0))
        ttk.Label(status, textvariable=self.status_var, style="InputLabel.TLabel").pack(
            side="left"
        )
        ttk.Label(
            status, textvariable=self.connection_var, style="InputLabel.TLabel"
        ).pack(side="right")

    @staticmethod
    def _thread_label(thread):
        title = thread.get("title") or "Nouvelle conversation"
        subject = thread.get("subject_label") or "Sans sujet"
        return f"{title}\n   {subject}"

    def refresh_subjects(self, preferred_key=None):
        previous = preferred_key or self.selected_subject_key()
        self.subjects = self.service.subject_options()
        self.subject_by_label.clear()
        labels = []
        counts = {}
        for item in self.subjects:
            base = item["label"]
            counts[base] = counts.get(base, 0) + 1
            label = base if counts[base] == 1 else f'{base}  (#{item.get("id")})'
            labels.append(label)
            self.subject_by_label[label] = item
        self.subject_box.configure(values=labels)
        selected = next(
            (label for label, item in self.subject_by_label.items()
             if item["key"] == previous),
            labels[0] if labels else "",
        )
        self.subject_var.set(selected)

    def selected_subject(self):
        return self.subject_by_label.get(self.subject_var.get()) or {
            "key": "general", "type": "general", "id": None,
            "label": "Sans sujet · discussion générale",
        }

    def selected_subject_key(self):
        subject = self.subject_by_label.get(self.subject_var.get())
        return subject.get("key") if subject else None

    def refresh_threads(self, select_id=None):
        self.thread_rows = self.store.list_chat_threads(100)
        self.thread_list.delete(0, "end")
        for thread in self.thread_rows:
            self.thread_list.insert("end", self._thread_label(thread))
        chosen = select_id if select_id is not None else self.current_thread_id
        if chosen is not None:
            for index, thread in enumerate(self.thread_rows):
                if thread["id"] == chosen:
                    self.thread_list.selection_set(index)
                    self.thread_list.see(index)
                    break

    def new_thread(self, preserve_subject=False):
        if self.waiting:
            return
        self.current_thread_id = None
        self.last_context = None
        self.delete_button.configure(state="disabled")
        self.thread_list.selection_clear(0, "end")
        if not preserve_subject and self.subjects:
            # Keep the current subject: creating another discussion about the same
            # person is the least surprising action.
            pass
        self._render_messages([])
        self._set_context_text(
            "Le contexte exact apparaîtra ici après sa préparation."
        )
        self.focus_var.set("")
        self.status_var.set("Nouvelle conversation · écris ta question à Emmett.")
        self._refresh_connection_label()
        self.input.focus_set()

    def _select_thread(self, _event=None):
        indices = self.thread_list.curselection()
        if not indices or self.waiting:
            return
        self.load_thread(self.thread_rows[indices[0]]["id"])

    def load_thread(self, thread_id):
        thread = self.store.get_chat_thread(thread_id)
        if not thread:
            return
        self.current_thread_id = thread["id"]
        key = (
            "general" if thread["subject_type"] == "general"
            else f'{thread["subject_type"]}:{thread["subject_id"]}'
        )
        self.refresh_subjects(key)
        self.angle_var.set(thread.get("reading_angle") or ANGLE_OPTIONS[0])
        rows = self.store.list_chat_messages(thread["id"])
        self._render_messages(rows)
        self.delete_button.configure(state="normal")
        self.store.touch_chat_thread(thread["id"])
        self.refresh_threads(thread["id"])
        self.last_context = None
        for row in reversed(rows):
            if row.get("context_json"):
                try:
                    self.last_context = json.loads(row["context_json"])
                except json.JSONDecodeError:
                    pass
                break
        if self.last_context is not None:
            self._display_context(self.last_context)
            self._display_focus(self.last_context)
        else:
            self.focus_var.set("")
        self.status_var.set(
            f'{thread["subject_label"]} · démarrée le {thread["target_date"]}'
        )
        self._refresh_connection_label()

    def delete_thread(self):
        if self.current_thread_id is None:
            return
        thread = self.store.get_chat_thread(self.current_thread_id)
        if not thread:
            return
        if not messagebox.askyesno(
            "Supprimer la conversation",
            f'Supprimer définitivement « {thread.get("title") or "Conversation"} » ?',
            parent=self,
        ):
            return
        self.store.delete_chat_thread(self.current_thread_id)
        self.current_thread_id = None
        self.refresh_threads()
        self.new_thread(preserve_subject=True)

    def _subject_changed(self, _event=None):
        if self.current_thread_id is not None:
            self.new_thread(preserve_subject=True)
        self.last_context = None
        self.status_var.set("Sujet prêt · le contexte sera recalculé au prochain envoi.")

    def _angle_changed(self, _event=None):
        if self.current_thread_id is not None:
            self.new_thread(preserve_subject=True)
        self.last_context = None
        self.status_var.set("Angle prêt · le contexte sera recalculé au prochain envoi.")

    def _moment(self):
        moment = self.moment_getter()
        if isinstance(moment, dict):
            return moment
        if isinstance(moment, (date, datetime)):
            return {"date": moment.date() if isinstance(moment, datetime) else moment}
        return {"date": date.today()}

    def _build_context(self, question="", previous_context=None):
        moment = self._moment()
        target = moment.get("date") or date.today()
        target_text = target.isoformat() if hasattr(target, "isoformat") else str(target)
        return self.service.build_context(
            self.selected_subject(), target_text,
            target_time=moment.get("time"), target_place=moment.get("place"),
            reading_angle=self.angle_var.get() or ANGLE_OPTIONS[0],
            question=question, previous_context=previous_context,
        )

    def send(self):
        if self.waiting:
            return
        question = self.input.get("1.0", "end-1c").strip()
        if not question:
            return
        if not self.client.configured():
            self.open_connection()
            if not self.client.configured():
                return
        try:
            context = self._build_context(
                question, previous_context=self.last_context
            )
        except Exception as error:
            messagebox.showerror("Contexte Emmett", str(error), parent=self)
            return

        subject = self.selected_subject()
        moment = self._moment()
        target = moment.get("date") or date.today()
        target_text = target.isoformat() if hasattr(target, "isoformat") else str(target)
        if self.current_thread_id is None:
            title = " ".join(question.split())[:64]
            thread = self.store.create_chat_thread(
                subject_type=subject["type"], subject_id=subject.get("id"),
                subject_label=subject["label"],
                reading_angle=self.angle_var.get() or ANGLE_OPTIONS[0],
                target_date=target_text, title=title,
            )
            self.current_thread_id = thread["id"]
        self.store.add_chat_message(
            self.current_thread_id, "user", question, context=context
        )
        self.last_context = context
        self._display_context(context)
        self._display_focus(context)
        self.input.delete("1.0", "end")
        messages = self.store.list_chat_messages(self.current_thread_id)
        self._render_messages(messages, pending=True)
        self.refresh_threads(self.current_thread_id)
        self._set_waiting(True)
        instructions = self.service.system_prompt()

        def success(result):
            if not self.winfo_exists() or self.current_thread_id is None:
                return
            self.store.add_chat_message(
                self.current_thread_id, "assistant", result["text"],
                model=result.get("model"), response_id=result.get("response_id"),
                input_tokens=result.get("input_tokens"),
                output_tokens=result.get("output_tokens"),
            )
            self._set_waiting(False)
            self._render_messages(
                self.store.list_chat_messages(self.current_thread_id)
            )
            self.refresh_threads(self.current_thread_id)
            parts = [f'Réponse reçue · {result.get("model") or self.client.model}']
            if result.get("input_tokens") is not None:
                parts.append(
                    f'{result["input_tokens"]} jetons envoyés · '
                    f'{result.get("output_tokens", 0)} reçus'
                )
            if result.get("retry_count"):
                parts.append("réponse relancée après une sortie incomplète")
            self.status_var.set(" · ".join(parts))

        def failure(error):
            if not self.winfo_exists():
                return
            self._set_waiting(False)
            self._render_messages(
                self.store.list_chat_messages(self.current_thread_id)
            )
            self.status_var.set("La réponse n’a pas été envoyée.")
            messagebox.showerror("Emmett", str(error), parent=self)

        self.jobs.submit(
            "olney_chat",
            lambda: self.client.respond(
                instructions=instructions, context=context, messages=messages
            ),
            success, failure,
        )

    def _send_shortcut(self, _event=None):
        if _event is not None and (_event.state & 0x0001):
            return None
        self.send()
        return "break"

    def _set_waiting(self, waiting):
        self.waiting = bool(waiting)
        state = "disabled" if waiting else "normal"
        self.send_button.configure(state=state)
        self.subject_box.configure(state="disabled" if waiting else "readonly")
        self.angle_box.configure(state="disabled" if waiting else "readonly")
        if waiting:
            self.status_var.set("Emmett relie les éléments de la lecture…")
        self._refresh_connection_label()

    def _render_messages(self, rows, pending=False):
        self.messages.configure(state="normal")
        self.messages.delete("1.0", "end")
        if not rows:
            self.messages.insert(
                "end",
                "Bonjour, je suis Emmett. Sélectionne ce que tu veux étudier puis "
                "pose-moi ta question. Je recevrai les calculs utiles du moteur, "
                "pas seulement ce qui est visible à l’écran.\n",
                "welcome",
            )
        for row in rows:
            role = row.get("role")
            if role == "user":
                self.messages.insert("end", "TOI\n", "user_heading")
                self.messages.insert("end", row.get("content", "") + "\n\n", "user")
            elif role == "assistant":
                self.messages.insert("end", "EMMETT\n", "assistant_heading")
                self.messages.insert(
                    "end", row.get("content", "") + "\n\n", "assistant"
                )
        if pending:
            self.messages.insert("end", "EMMETT\n", "assistant_heading")
            self.messages.insert("end", "Je relie les éléments…\n", "pending")
        self.messages.configure(state="disabled")
        self.messages.see("end")

    def toggle_context(self):
        self.context_visible = not self.context_visible
        if self.context_visible:
            if self.last_context is None:
                try:
                    self.last_context = self._build_context()
                    self._display_context(self.last_context)
                except Exception as error:
                    self._set_context_text(str(error))
            self.context_shell.pack(fill="both", pady=(8, 0), before=self.input.master)
            self.context_button.configure(text="MASQUER LE CONTEXTE")
        else:
            self.context_shell.pack_forget()
            self.context_button.configure(text="VOIR LE CONTEXTE")

    def _display_context(self, context):
        self._set_context_text(json.dumps(context, ensure_ascii=False, indent=2))

    def _display_focus(self, context):
        request = (context or {}).get("chat_request") or {}
        base = request.get("base_subject") or {}
        effective = request.get("effective_subject") or {}
        route = request.get("routing")
        if route == "ambiguous_event":
            self.focus_var.set("FOCUS · Plusieurs événements correspondent à la demande")
            return
        if route == "ambiguous_relationship":
            self.focus_var.set("FOCUS · Plusieurs relations correspondent à la demande")
            return
        if effective and (
            effective.get("type") != base.get("type")
            or effective.get("id") != base.get("id")
        ):
            self.focus_var.set(f'FOCUS DU MESSAGE · {effective.get("label", "")})')
            return
        if route in {"relative_date", "explicit_date"}:
            self.focus_var.set(f'DATE DU MESSAGE · {request.get("requested_at", "")}')
            return
        self.focus_var.set("")

    def _set_context_text(self, content):
        self.context_text.configure(state="normal")
        self.context_text.delete("1.0", "end")
        self.context_text.insert("1.0", str(content))
        self.context_text.configure(state="disabled")

    def open_connection(self):
        dialog = tk.Toplevel(self)
        dialog.title("Connexion IA — session Emmett")
        dialog.transient(self.winfo_toplevel())
        dialog.resizable(False, False)
        shell = ttk.Frame(dialog, padding=18)
        shell.pack(fill="both", expand=True)
        ttk.Label(shell, text="CONNEXION EMMETT", font=("Segoe UI", 14, "bold")).pack(
            anchor="w"
        )
        ttk.Label(
            shell,
            text=(
                "La clé sert uniquement pendant cette session. Elle n’est ni "
                "enregistrée dans la base locale. Les messages et le contexte utile "
                "sont transmis au service choisi (et à son fournisseur de modèle via OpenRouter)."
            ),
            wraplength=470, justify="left",
        ).pack(anchor="w", pady=(5, 13))
        ttk.Label(shell, text="SERVICE", style="InputLabel.TLabel").pack(anchor="w")
        provider_var = tk.StringVar(value="OpenRouter" if self.client.provider == "openrouter" else "OpenAI")
        provider_entry = ttk.Combobox(shell, textvariable=provider_var,
                                      values=("OpenRouter", "OpenAI"), state="readonly")
        provider_entry.pack(fill="x", pady=(4, 10))
        ttk.Label(shell, text="CLÉ API", style="InputLabel.TLabel").pack(anchor="w")
        key_var = tk.StringVar()
        key_entry = ttk.Entry(
            shell, textvariable=key_var, show="•", width=58, style="Input.TEntry"
        )
        key_entry.pack(fill="x", pady=(4, 10))
        ttk.Label(shell, text="MODÈLE", style="InputLabel.TLabel").pack(anchor="w")
        model_var = tk.StringVar(value=self.client.model or DEFAULT_MODEL)
        model_entry = ttk.Entry(
            shell, textvariable=model_var, width=32, style="Input.TEntry"
        )
        model_entry.pack(fill="x", pady=(4, 10))
        detected = (
            "Une clé est déjà active pour cette session."
            if self.client.configured() else
            "Clés possibles : OPENAI_API_KEY ou OPENROUTER_API_KEY."
        )
        ttk.Label(shell, text=detected, style="InputLabel.TLabel").pack(anchor="w")
        ttk.Label(shell, text="OpenRouter : indique l’identifiant exact du modèle, ou openrouter/auto.",
                  wraplength=470).pack(anchor="w", pady=(5, 0))

        def change_provider(_event=None):
            provider = provider_var.get().lower()
            key_var.set("")
            saved = self.client._connections.get(provider)
            model_var.set(self.client.model if provider == self.client.provider else
                          saved[1] if saved else
                          OPENROUTER_MODEL if provider == "openrouter" else DEFAULT_MODEL)

        provider_entry.bind("<<ComboboxSelected>>", change_provider)

        buttons = ttk.Frame(shell)
        buttons.pack(fill="x", pady=(14, 0))

        def apply_connection():
            key = key_var.get().strip()
            model = model_var.get().strip()
            try:
                self.client.configure_connection(provider_var.get().lower(), key, model)
            except ValueError as error:
                messagebox.showerror(
                    "Connexion Emmett", str(error), parent=dialog
                )
                return
            dialog.destroy()
            self._refresh_connection_label()
            self.status_var.set(f"Connexion prête · modèle {model}.")

        ttk.Button(buttons, text="ANNULER", command=dialog.destroy).pack(side="right")
        ttk.Button(
            buttons, text="APPLIQUER À CETTE SESSION",
            style="Calculate.TButton", command=apply_connection,
        ).pack(side="right", padx=(0, 7))
        dialog.update_idletasks()
        parent = self.winfo_toplevel()
        x = parent.winfo_rootx() + max(0, (parent.winfo_width() - dialog.winfo_width()) // 2)
        y = parent.winfo_rooty() + max(0, (parent.winfo_height() - dialog.winfo_height()) // 2)
        dialog.geometry(f"+{x}+{y}")
        key_entry.focus_set()

    def _refresh_connection_label(self):
        if self.waiting:
            self.connection_var.set("◐ RÉPONSE EN COURS")
        elif self.client.configured():
            self.connection_var.set(f"● {self.client.provider.upper()} · {self.client.model}")
        else:
            self.connection_var.set("○ IA NON CONNECTÉE")

    def apply_theme(self):
        dark = bool(self.dark_mode_getter())
        bg = "#0D141C" if dark else LIGHT["bg"]
        panel = "#151F29" if dark else LIGHT["panel"]
        raised = "#1C2A36" if dark else LIGHT["raised"]
        field = "#101922" if dark else LIGHT["field"]
        fg = "#E7EEF5" if dark else LIGHT["text"]
        muted = "#AFC0CE" if dark else LIGHT["muted"]
        blue = "#79B8EA" if dark else LIGHT["accent"]
        green = "#72D2AE" if dark else LIGHT["green"]
        border = "#405465" if dark else LIGHT["line"]

        self.message_shell.configure(background=panel, highlightbackground=border)
        self.messages.configure(
            background=panel, foreground=fg, insertbackground=fg,
            selectbackground="#35536B" if dark else LIGHT["selected"],
        )
        self.messages.tag_configure("welcome", foreground=muted, spacing1=12)
        self.messages.tag_configure(
            "user_heading", foreground=blue, font=("Segoe UI", 9, "bold")
        )
        self.messages.tag_configure("user", foreground=fg, lmargin1=14, lmargin2=14)
        self.messages.tag_configure(
            "assistant_heading", foreground=green, font=("Segoe UI", 9, "bold")
        )
        self.messages.tag_configure(
            "assistant", foreground=fg, lmargin1=14, lmargin2=14
        )
        self.messages.tag_configure("pending", foreground=muted, lmargin1=14)
        self.input.configure(
            background=field, foreground=fg, insertbackground=fg,
            highlightbackground=border, highlightcolor=blue,
            selectbackground="#35536B" if dark else LIGHT["selected"],
        )
        self.thread_list.configure(
            background=panel, foreground=fg,
            selectbackground="#29465E" if dark else LIGHT["selected"],
            selectforeground=fg, highlightbackground=border,
        )
        self.context_shell.configure(background=panel, highlightbackground=border)
        self.context_title.configure(background=raised, foreground=green)
        self.context_text.configure(
            background=panel, foreground=fg, insertbackground=fg,
            selectbackground="#35536B" if dark else LIGHT["selected"],
        )
        self.configure(style="TFrame")
        self._refresh_connection_label()

    def destroy(self):
        self.jobs.cancel("olney_chat")
        super().destroy()
