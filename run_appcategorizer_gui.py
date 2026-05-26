import asyncio
import queue
import threading
import tkinter as tk
from tkinter import messagebox

import ttkbootstrap as ttk
from ttkbootstrap.constants import BOTH, DISABLED, END, LEFT, NORMAL, X

from appcategorizer import Categorizer


class AppCategorizerGui:
    def __init__(self, root: ttk.Window):
        self.root = root
        self.root.title("appcategorizer")
        self.root.geometry("560x390")
        self.root.minsize(480, 340)

        self.events: queue.Queue[tuple[str, str]] = queue.Queue()
        self.worker: threading.Thread | None = None

        self.app_name = tk.StringVar()
        self.status = tk.StringVar(value="Ready")
        self.result = tk.StringVar(value="No category yet")

        self._build_ui()
        self.root.after(100, self._drain_events)

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
        ).pack(anchor="w", pady=(2, 18))

        input_row = ttk.Frame(container)
        input_row.pack(fill=X)

        self.entry = ttk.Entry(input_row, textvariable=self.app_name)
        self.entry.pack(side=LEFT, fill=X, expand=True)
        self.entry.bind("<Return>", lambda _event: self.classify())

        self.button = ttk.Button(
            input_row,
            text="Classify",
            command=self.classify,
            bootstyle="primary",
        )
        self.button.pack(side=LEFT, padx=(10, 0))

        result_frame = ttk.Labelframe(container, text="Result", padding=14)
        result_frame.pack(fill=X, pady=(18, 12))

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
        ).pack(anchor="w", pady=(0, 8))

        self.progress = ttk.Progressbar(
            container,
            mode="indeterminate",
            bootstyle="info-striped",
        )
        self.progress.pack(fill=X, pady=(0, 12))

        self.log = tk.Text(
            container,
            height=8,
            wrap="word",
            relief="flat",
            borderwidth=0,
            padx=10,
            pady=10,
        )
        self.log.pack(fill=BOTH, expand=True)
        self.log.configure(state=DISABLED)

        self.entry.focus_set()

    def classify(self) -> None:
        name = self.app_name.get().strip()
        if not name:
            messagebox.showinfo("Application name required", "Enter an application name first.")
            self.entry.focus_set()
            return

        if self.worker is not None and self.worker.is_alive():
            return

        self.result.set("Classifying...")
        self.status.set("Starting...")
        self._clear_log()
        self._set_busy(True)

        self.worker = threading.Thread(
            target=self._classify_in_worker,
            args=(name,),
            daemon=True,
        )
        self.worker.start()

    def _classify_in_worker(self, name: str) -> None:
        def on_progress(message: str) -> None:
            self.events.put(("progress", message))

        async def run() -> str:
            categorizer = Categorizer(on_progress=on_progress)
            return await categorizer.resolve_and_classify(name)

        try:
            category = asyncio.run(run())
        except Exception as exc:
            self.events.put(("error", f"{exc.__class__.__name__}: {exc}"))
        else:
            self.events.put(("result", category))

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
        self.button.configure(state=DISABLED if busy else NORMAL)
        self.entry.configure(state=DISABLED if busy else NORMAL)
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
