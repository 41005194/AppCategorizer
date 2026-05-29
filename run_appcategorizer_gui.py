import asyncio
import queue
import threading
import tkinter as tk
from tkinter import messagebox

import ttkbootstrap as ttk
from ttkbootstrap.constants import BOTH, DISABLED, END, LEFT, NORMAL, X

from appcategorizer import Categorizer
from appcategorizer.engine.llm_classifier import KNOWN_PROVIDERS

# Pre-defined model lists per provider. The combobox is editable so the user
# can also type any model name that isn't listed here.
PROVIDER_MODELS: dict[str, list[str]] = {
    "openai":    ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o1", "o1-mini", "o3-mini"],
    "anthropic": ["claude-opus-4-6", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"],
    "mistral":   ["mistral-large-latest", "mistral-small-latest", "open-mistral-nemo"],
    "gemini":    ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-pro", "gemini-1.5-flash"],
    "ollama":    ["llama3.2", "llama3.1", "mistral", "phi3", "gemma2", "qwen2.5"],
    "custom":    [],
}

# Providers that require a base URL (shown as an extra field).
_URL_PROVIDERS = {"ollama", "custom"}

_ML_GEOMETRY  = "560x430"
_ML_MINSIZE   = (480, 370)
_LLM_GEOMETRY = "600x590"
_LLM_MINSIZE  = (520, 520)


class AppCategorizerGui:
    def __init__(self, root: ttk.Window):
        self.root = root
        self.root.title("appcategorizer")
        self.root.geometry(_ML_GEOMETRY)
        self.root.minsize(*_ML_MINSIZE)

        self.events: queue.Queue[tuple[str, str]] = queue.Queue()
        self.worker: threading.Thread | None = None

        # Shared state
        self.app_name = tk.StringVar()
        self.status   = tk.StringVar(value="Ready")
        self.result   = tk.StringVar(value="No category yet")
        self._mode    = "local_ml"

        # LLM state — preserved across mode switches for the session
        self._llm_provider_var = tk.StringVar(value=KNOWN_PROVIDERS[0])
        self._llm_model_var    = tk.StringVar(value=PROVIDER_MODELS[KNOWN_PROVIDERS[0]][0])
        self._llm_api_key_var  = tk.StringVar()
        self._llm_base_url_var = tk.StringVar()

        self._build_ui()
        self.root.after(100, self._drain_events)

    # ------------------------------------------------------------------ #
    # UI construction                                                      #
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, padding=18)
        container.pack(fill=BOTH, expand=True)

        ttk.Label(
            container,
            text="App Categorizer",
            font=("TkDefaultFont", 18, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            container,
            text="Enter an application name and classify it with the library.",
            bootstyle="secondary",
        ).pack(anchor="w", pady=(2, 12))

        # Input row
        input_row = ttk.Frame(container)
        input_row.pack(fill=X)

        self.entry = ttk.Entry(input_row, textvariable=self.app_name)
        self.entry.pack(side=LEFT, fill=X, expand=True)
        self.entry.bind("<Return>", lambda _: self.classify())

        self.button = ttk.Button(
            input_row,
            text="Classify",
            command=self.classify,
            bootstyle="primary",
        )
        self.button.pack(side=LEFT, padx=(10, 0))

        # Mode toggle
        self._toggle_frame = ttk.Frame(container)
        self._toggle_frame.pack(anchor="w", pady=(10, 0))

        self._ml_btn = ttk.Button(
            self._toggle_frame,
            text="ML",
            width=6,
            bootstyle="primary",
            command=lambda: self._set_mode("local_ml"),
        )
        self._ml_btn.pack(side=LEFT)

        self._llm_btn = ttk.Button(
            self._toggle_frame,
            text="LLM",
            width=6,
            bootstyle="outline",
            command=lambda: self._set_mode("cloud_llm"),
        )
        self._llm_btn.pack(side=LEFT, padx=(2, 0))

        # LLM config panel — built now but not packed (hidden in ML mode)
        self._llm_frame = ttk.Labelframe(container, text="LLM Configuration", padding=12)
        self._build_llm_panel()

        # Result
        result_frame = ttk.Labelframe(container, text="Result", padding=14)
        result_frame.pack(fill=X, pady=(12, 12))

        ttk.Label(
            result_frame,
            textvariable=self.result,
            font=("TkDefaultFont", 16, "bold"),
            bootstyle="primary",
        ).pack(anchor="w")

        ttk.Label(
            container,
            textvariable=self.status,
            bootstyle="secondary",
        ).pack(anchor="w", pady=(0, 6))

        self.progress = ttk.Progressbar(
            container,
            mode="indeterminate",
            bootstyle="info-striped",
        )
        self.progress.pack(fill=X, pady=(0, 10))

        self.log = tk.Text(
            container,
            height=7,
            wrap="word",
            relief="flat",
            borderwidth=0,
            padx=10,
            pady=10,
        )
        self.log.pack(fill=BOTH, expand=True)
        self.log.configure(state=DISABLED)

        self.entry.focus_set()

    def _build_llm_panel(self) -> None:
        """Populate the LLM configuration panel (inside self._llm_frame)."""
        parent = self._llm_frame

        # Provider
        provider_row = ttk.Frame(parent)
        provider_row.pack(fill=X, pady=(0, 6))
        ttk.Label(provider_row, text="Provider", width=10, anchor="w").pack(side=LEFT)
        self._provider_combo = ttk.Combobox(
            provider_row,
            textvariable=self._llm_provider_var,
            values=KNOWN_PROVIDERS,
            state="readonly",
            width=22,
        )
        self._provider_combo.pack(side=LEFT, fill=X, expand=True)
        self._llm_provider_var.trace_add("write", self._on_provider_change)

        # Model
        model_row = ttk.Frame(parent)
        model_row.pack(fill=X, pady=(0, 6))
        ttk.Label(model_row, text="Model", width=10, anchor="w").pack(side=LEFT)
        self._model_combo = ttk.Combobox(
            model_row,
            textvariable=self._llm_model_var,
            values=PROVIDER_MODELS[self._llm_provider_var.get()],
            width=22,
        )
        self._model_combo.pack(side=LEFT, fill=X, expand=True)

        # API Key
        key_row = ttk.Frame(parent)
        key_row.pack(fill=X, pady=(0, 6))
        ttk.Label(key_row, text="API Key", width=10, anchor="w").pack(side=LEFT)
        self._api_key_entry = ttk.Entry(
            key_row,
            textvariable=self._llm_api_key_var,
            show="*",
            width=22,
        )
        self._api_key_entry.pack(side=LEFT, fill=X, expand=True)

        # Base URL — conditionally shown for ollama / custom
        self._base_url_row = ttk.Frame(parent)
        ttk.Label(self._base_url_row, text="Base URL", width=10, anchor="w").pack(side=LEFT)
        ttk.Entry(
            self._base_url_row,
            textvariable=self._llm_base_url_var,
            width=22,
        ).pack(side=LEFT, fill=X, expand=True)
        # Not packed yet; _refresh_base_url_row handles visibility.

    # ------------------------------------------------------------------ #
    # Mode switching                                                       #
    # ------------------------------------------------------------------ #

    def _set_mode(self, mode: str) -> None:
        if mode == self._mode:
            return
        self._mode = mode

        if mode == "local_ml":
            self._ml_btn.configure(bootstyle="primary")
            self._llm_btn.configure(bootstyle="outline")
            self._llm_frame.pack_forget()
            self.root.minsize(*_ML_MINSIZE)
            self.root.geometry(_ML_GEOMETRY)
        else:
            self._ml_btn.configure(bootstyle="outline")
            self._llm_btn.configure(bootstyle="primary")
            # Insert the panel immediately after the toggle row.
            self._llm_frame.pack(fill=X, pady=(10, 0), after=self._toggle_frame)
            self.root.minsize(*_LLM_MINSIZE)
            self.root.geometry(_LLM_GEOMETRY)
            self._refresh_base_url_row()

    def _on_provider_change(self, *_args) -> None:
        provider = self._llm_provider_var.get()
        models = PROVIDER_MODELS.get(provider, [])
        self._model_combo["values"] = models
        if models and self._llm_model_var.get() not in models:
            self._llm_model_var.set(models[0])
        elif not models:
            self._llm_model_var.set("")
        self._refresh_base_url_row()

    def _refresh_base_url_row(self) -> None:
        """Show or hide the Base URL field depending on the selected provider."""
        if self._llm_provider_var.get() in _URL_PROVIDERS:
            self._base_url_row.pack(fill=X)
        else:
            self._base_url_row.pack_forget()

    # ------------------------------------------------------------------ #
    # Classification                                                       #
    # ------------------------------------------------------------------ #

    def classify(self) -> None:
        name = self.app_name.get().strip()
        if not name:
            messagebox.showinfo("Application name required", "Enter an application name first.")
            self.entry.focus_set()
            return

        if self._mode == "cloud_llm" and not self._llm_provider_var.get():
            messagebox.showwarning("Provider required", "Select an LLM provider first.")
            return

        if self.worker is not None and self.worker.is_alive():
            return

        self.result.set("Classifying...")
        self.status.set("Starting...")
        self._clear_log()
        self._set_busy(True)

        # Snapshot LLM params before handing off to the worker thread so that
        # any subsequent UI change does not affect the running request.
        llm_params = (
            {
                "llm_provider": self._llm_provider_var.get() or None,
                "llm_model":    self._llm_model_var.get() or None,
                "llm_api_key":  self._llm_api_key_var.get() or None,
                "llm_base_url": self._llm_base_url_var.get() or None,
            }
            if self._mode == "cloud_llm"
            else {}
        )

        self.worker = threading.Thread(
            target=self._classify_in_worker,
            args=(name, self._mode, llm_params),
            daemon=True,
        )
        self.worker.start()

    def _classify_in_worker(self, name: str, mode: str, llm_params: dict) -> None:
        def on_progress(message: str) -> None:
            self.events.put(("progress", message))

        async def run() -> str:
            categorizer = Categorizer(on_progress=on_progress)
            return await categorizer.resolve_and_classify(
                name,
                analysis_mode=mode,
                **llm_params,
            )

        try:
            category = asyncio.run(run())
        except Exception as exc:
            self.events.put(("error", f"{exc.__class__.__name__}: {exc}"))
        else:
            self.events.put(("result", category))

    # ------------------------------------------------------------------ #
    # Event draining / UI updates                                          #
    # ------------------------------------------------------------------ #

    def _drain_events(self) -> None:
        while True:
            try:
                event_type, message = self.events.get_nowait()
            except queue.Empty:
                break

            if event_type == "progress":
                self.status.set(message)
                self._append_log(message)
            elif event_type == "result":
                self.result.set(message)
                self.status.set("Done")
                self._set_busy(False)
            elif event_type == "error":
                self.result.set("Failed")
                self.status.set(message)
                self._append_log(message)
                self._set_busy(False)

        self.root.after(100, self._drain_events)

    def _set_busy(self, busy: bool) -> None:
        state = DISABLED if busy else NORMAL
        self.button.configure(state=state)
        self.entry.configure(state=state)
        # Disable the toggle while a classification is running.
        self._ml_btn.configure(state=state)
        self._llm_btn.configure(state=state)
        if busy:
            self.progress.start(12)
        else:
            self.progress.stop()
            self.entry.focus_set()

    def _append_log(self, message: str) -> None:
        self.log.configure(state=NORMAL)
        self.log.insert(END, f"{message}\n")
        self.log.see(END)
        self.log.configure(state=DISABLED)

    def _clear_log(self) -> None:
        self.log.configure(state=NORMAL)
        self.log.delete("1.0", END)
        self.log.configure(state=DISABLED)


def main() -> None:
    root = ttk.Window(themename="flatly")
    AppCategorizerGui(root)
    root.mainloop()


if __name__ == "__main__":
    main()