"""Reusable CustomTkinter pages for SEO Inspector Pro."""
from __future__ import annotations

import tkinter as tk
import webbrowser
from collections.abc import Callable
from typing import Any

import customtkinter as ctk
from PIL import Image, ImageTk

from src.models.crawl_models import PageResult

BG = "#111827"
PANEL = "#1f2937"
ACCENT = "#38bdf8"
TEXT = "#e5e7eb"
MUTED = "#9ca3af"


class TablePage(ctk.CTkFrame):
    """A searchable list page backed by a Tk Listbox."""

    def __init__(self, master: ctk.CTkBaseClass, title: str, columns: list[str]) -> None:
        super().__init__(master, fg_color=BG)
        self.title = title
        self.columns = columns
        self.rows: list[tuple[str, ...]] = []
        ctk.CTkLabel(self, text=title, font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w", padx=24, pady=(22, 8))
        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.pack(fill="x", padx=24, pady=(0, 12))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.refresh())
        ctk.CTkEntry(controls, textvariable=self.search_var, placeholder_text="Search or filter results...").pack(side="left", fill="x", expand=True)
        ctk.CTkButton(controls, text="Clear", width=80, command=lambda: self.search_var.set("")).pack(side="left", padx=(10, 0))
        self.header = ctk.CTkLabel(self, text="  |  ".join(columns), text_color=ACCENT, anchor="w", font=ctk.CTkFont(weight="bold"))
        self.header.pack(fill="x", padx=24)
        self.listbox = tk.Listbox(self, bg=PANEL, fg=TEXT, selectbackground="#075985", relief="flat", highlightthickness=0, font=("Consolas", 10))
        self.listbox.pack(fill="both", expand=True, padx=24, pady=(6, 24))
        self.listbox.bind("<Double-Button-1>", self._open_selected_url)

    def set_rows(self, rows: list[tuple[Any, ...]]) -> None:
        self.rows = [tuple(str(item) for item in row) for row in rows]
        self.refresh()

    def refresh(self) -> None:
        query = self.search_var.get().lower()
        self.listbox.delete(0, tk.END)
        for row in self.rows:
            line = "  |  ".join(row)
            if not query or query in line.lower():
                self.listbox.insert(tk.END, line)

    def _open_selected_url(self, _event: tk.Event) -> None:
        selection = self.listbox.curselection()
        if selection:
            first = self.listbox.get(selection[0]).split("  |  ", 1)[0]
            if first.startswith(("http://", "https://")):
                webbrowser.open(first)


class DashboardPage(ctk.CTkFrame):
    """Live crawl metrics dashboard."""

    def __init__(self, master: ctk.CTkBaseClass) -> None:
        super().__init__(master, fg_color=BG)
        ctk.CTkLabel(self, text="Dashboard", font=ctk.CTkFont(size=26, weight="bold")).pack(anchor="w", padx=24, pady=(22, 12))
        self.cards = ctk.CTkFrame(self, fg_color="transparent")
        self.cards.pack(fill="x", padx=18)
        self.metric_labels: dict[str, ctk.CTkLabel] = {}
        for index, name in enumerate(["Total Pages", "Internal Links", "External Links", "Images", "Broken Links", "SEO Score", "Average Response Time"]):
            card = ctk.CTkFrame(self.cards, fg_color=PANEL, corner_radius=14)
            card.grid(row=index // 4, column=index % 4, padx=6, pady=6, sticky="ew")
            self.cards.grid_columnconfigure(index % 4, weight=1)
            ctk.CTkLabel(card, text=name, text_color=MUTED).pack(anchor="w", padx=14, pady=(12, 2))
            label = ctk.CTkLabel(card, text="0", font=ctk.CTkFont(size=24, weight="bold"))
            label.pack(anchor="w", padx=14, pady=(0, 14))
            self.metric_labels[name] = label
        self.status_box = tk.Listbox(self, height=12, bg=PANEL, fg=TEXT, selectbackground="#075985", relief="flat", highlightthickness=0)
        self.status_box.pack(fill="both", expand=True, padx=24, pady=18)

    def update_metrics(self, pages: list[PageResult], score: int) -> None:
        internal = sum(1 for p in pages for link in p.links if link.get("type") == "internal")
        external = sum(1 for p in pages for link in p.links if link.get("type") == "external")
        images = sum(len(p.images) for p in pages)
        broken = sum(1 for p in pages for link in p.links if link.get("status") == "broken")
        avg = sum(p.response_time for p in pages) / max(1, len(pages))
        values = {"Total Pages": len(pages), "Internal Links": internal, "External Links": external, "Images": images, "Broken Links": broken, "SEO Score": f"{score}/100", "Average Response Time": f"{avg:.2f}s"}
        for name, value in values.items():
            self.metric_labels[name].configure(text=str(value))
        status_counts: dict[int, int] = {}
        for page in pages:
            status_counts[page.status_code] = status_counts.get(page.status_code, 0) + 1
        self.status_box.delete(0, tk.END)
        self.status_box.insert(tk.END, "HTTP Status Distribution")
        for code, count in sorted(status_counts.items()):
            self.status_box.insert(tk.END, f"{code}: {'█' * min(count, 60)} {count}")


class ExportPage(ctk.CTkFrame):
    """Professional report export interface."""

    def __init__(self, master: ctk.CTkBaseClass, on_export: Callable[[str], None]) -> None:
        super().__init__(master, fg_color=BG)
        self.on_export = on_export
        ctk.CTkLabel(self, text="Export", font=ctk.CTkFont(size=26, weight="bold")).pack(anchor="w", padx=24, pady=(22, 12))
        ctk.CTkLabel(self, text="Generate production-ready SEO audit deliverables from the current crawl data.", text_color=MUTED).pack(anchor="w", padx=24, pady=(0, 18))
        grid = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=14)
        grid.pack(fill="x", padx=24, pady=10)
        actions = [
            ("Export Excel", "excel", "SEO_Report.xlsx with worksheets for every primary audit section."),
            ("Export CSV", "csv", "Separate CSV files for pages, SEO, media, links, resources, emails, security, and social data."),
            ("Export JSON", "json", "Report.json with safe serialization for dates, paths, UUIDs, enums, decimals, and sets."),
            ("Export HTML", "html", "Responsive dashboard report with score, charts, statistics, issues, and recommendations."),
            ("Export ZIP", "zip", "Creates every report file and compresses the package into SEO_Report.zip."),
        ]
        for index, (label, export_type, description) in enumerate(actions):
            card = ctk.CTkFrame(grid, fg_color="#111827", corner_radius=12)
            card.grid(row=index // 2, column=index % 2, padx=14, pady=14, sticky="nsew")
            grid.grid_columnconfigure(index % 2, weight=1)
            ctk.CTkLabel(card, text=label, font=ctk.CTkFont(size=16, weight="bold"), anchor="w").pack(fill="x", padx=14, pady=(14, 4))
            ctk.CTkLabel(card, text=description, text_color=MUTED, anchor="w", justify="left", wraplength=420).pack(fill="x", padx=14, pady=(0, 12))
            ctk.CTkButton(card, text=label, height=38, command=lambda kind=export_type: self.on_export(kind)).pack(fill="x", padx=14, pady=(0, 14))
        ctk.CTkLabel(self, text="Files are written to the reports folder. If one format fails during ZIP export, remaining formats continue and failures are reported.", text_color=MUTED, wraplength=820, justify="left").pack(anchor="w", padx=24, pady=18)


class SettingsPage(ctk.CTkFrame):
    """Application settings form."""

    def __init__(self, master: ctk.CTkBaseClass) -> None:
        super().__init__(master, fg_color=BG)
        ctk.CTkLabel(self, text="Settings", font=ctk.CTkFont(size=26, weight="bold")).pack(anchor="w", padx=24, pady=(22, 14))
        self.values: dict[str, tk.StringVar] = {}
        for label, default in [("Theme", "Dark"), ("Maximum Threads", "10"), ("Timeout", "20"), ("User-Agent", "SEO Inspector Pro/1.0"), ("Default Export Folder", "reports")]:
            row = ctk.CTkFrame(self, fg_color="transparent")
            row.pack(fill="x", padx=24, pady=8)
            ctk.CTkLabel(row, text=label, width=180, anchor="w").pack(side="left")
            var = tk.StringVar(value=default)
            ctk.CTkEntry(row, textvariable=var).pack(side="left", fill="x", expand=True)
            self.values[label] = var
