#!/usr/bin/env python3
"""GUI for preparing a phpBB FTP clone for Discourse."""

from __future__ import annotations

import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText


class MigrationGui:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("Préparation phpBB → Discourse")
        root.geometry("780x520")
        self.project_root = Path(__file__).resolve().parents[1]
        self.clone_path, self.original_host = tk.StringVar(), tk.StringVar(value="surfrepotes.fr/forum")
        self.status = tk.StringVar(value="Prêt")
        self.output: queue.Queue[str] = queue.Queue()
        self.process: subprocess.Popen[str] | None = None
        self.build()
        root.after(150, self.poll)

    def build(self) -> None:
        frame = ttk.Frame(self.root, padding=18)
        frame.pack(fill=tk.BOTH, expand=True)
        frame.columnconfigure(1, weight=1)
        ttk.Label(frame, text="Migration du contenu phpBB vers Discourse", font=("Segoe UI", 16, "bold")).grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(frame, text="Sélectionne le clone FTP : la dernière sauvegarde SQL de forum/store sera détectée automatiquement.").grid(row=1, column=0, columnspan=3, sticky="w", pady=(2, 14))
        ttk.Label(frame, text="Clone FTP").grid(row=2, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.clone_path).grid(row=2, column=1, sticky="ew", padx=8)
        ttk.Button(frame, text="Parcourir…", command=self.select_clone).grid(row=2, column=2)
        ttk.Label(frame, text="Ancien hôte / chemin").grid(row=3, column=0, sticky="w", pady=8)
        ttk.Entry(frame, textvariable=self.original_host).grid(row=3, column=1, columnspan=2, sticky="ew", padx=8, pady=8)
        actions = ttk.Frame(frame)
        actions.grid(row=4, column=0, columnspan=3, sticky="ew", pady=8)
        self.start_button = ttk.Button(actions, text="Préparer l'import Discourse", command=self.start)
        self.start_button.pack(side=tk.LEFT)
        ttk.Label(actions, textvariable=self.status).pack(side=tk.RIGHT)
        self.log = ScrolledText(frame, height=18, state=tk.DISABLED, wrap=tk.WORD, font=("Consolas", 9))
        self.log.grid(row=5, column=0, columnspan=3, sticky="nsew", pady=(8, 0))
        frame.rowconfigure(5, weight=1)

    def select_clone(self) -> None:
        selected = filedialog.askdirectory(title="Clone FTP contenant www/forum")
        if selected:
            self.clone_path.set(selected)

    def append(self, line: str) -> None:
        self.log.configure(state=tk.NORMAL)
        self.log.insert(tk.END, line + "\n")
        self.log.see(tk.END)
        self.log.configure(state=tk.DISABLED)

    def start(self) -> None:
        if not self.clone_path.get().strip() or not self.original_host.get().strip():
            messagebox.showerror("Information manquante", "Indique le clone FTP et l'ancien hôte / chemin.")
            return
        command = [sys.executable, str(self.project_root / "scripts" / "orchestrate_migration.py"),
                   "--clone-path", self.clone_path.get().strip(), "--original-host", self.original_host.get().strip()]
        self.start_button.configure(state=tk.DISABLED)
        self.status.set("Préparation en cours…")
        self.process = subprocess.Popen(command, cwd=self.project_root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
        threading.Thread(target=self.read_output, daemon=True).start()

    def read_output(self) -> None:
        assert self.process and self.process.stdout
        for line in self.process.stdout:
            self.output.put(line.rstrip())
        self.output.put(f"__EXIT__:{self.process.wait()}")

    def poll(self) -> None:
        try:
            while True:
                line = self.output.get_nowait()
                if line.startswith("__EXIT__:"):
                    code = int(line.split(":", 1)[1])
                    self.status.set("Prêt pour l'import Discourse" if code == 0 else f"Erreur (code {code})")
                    self.start_button.configure(state=tk.NORMAL)
                else:
                    self.append(line)
        except queue.Empty:
            pass
        self.root.after(150, self.poll)


if __name__ == "__main__":
    root = tk.Tk()
    MigrationGui(root)
    root.mainloop()
