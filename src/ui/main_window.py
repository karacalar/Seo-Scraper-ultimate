"""Main CustomTkinter window for SEO Inspector Pro."""
from __future__ import annotations

import asyncio
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from src.analyzer.seo_analyzer import SEOAnalyzer
from src.crawler.async_crawler import AsyncCrawler
from src.models.crawl_models import PageResult
from src.exporter.report_exporter import ReportExporter
from src.parser.site_discovery import SiteDiscovery
from src.ui.pages import DashboardPage, ExportPage, SettingsPage, TablePage


class MainWindow(ctk.CTk):
    """Single-window desktop application with persistent managed pages."""

    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.title("SEO Inspector Pro - Professional Website Crawling & SEO Auditing Tool")
        self.geometry("1440x900")
        self.minsize(1180, 760)
        self.pages: list[PageResult] = []
        self.analyzer = SEOAnalyzer()
        self.discovery = SiteDiscovery()
        self.exporter = ReportExporter(Path("reports"))
        self.crawler = AsyncCrawler(self._receive_page_threadsafe, self._receive_status_threadsafe)
        self.crawler_thread: threading.Thread | None = None
        self.loop: asyncio.AbstractEventLoop | None = None
        self._build_layout()
        self._build_pages()
        self.show_page("Dashboard")

    def _build_layout(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.sidebar = ctk.CTkFrame(self, width=210, corner_radius=0, fg_color="#0f172a")
        self.sidebar.grid(row=0, column=0, rowspan=3, sticky="nsew")
        ctk.CTkLabel(self.sidebar, text="SEO Inspector Pro", font=ctk.CTkFont(size=20, weight="bold"), text_color="#38bdf8").pack(padx=14, pady=(20, 4))
        ctk.CTkLabel(self.sidebar, text="Professional Website Crawling\n& SEO Auditing Tool", text_color="#94a3b8").pack(padx=14, pady=(0, 16))
        self.nav_buttons: dict[str, ctk.CTkButton] = {}
        for name in ["Dashboard", "Pages", "SEO Analysis", "Images", "Links", "Resources", "Emails", "Social Media", "Security", "Sitemaps", "Robots.txt", "Export", "Settings"]:
            button = ctk.CTkButton(self.sidebar, text=name, anchor="w", height=34, command=lambda page=name: self.show_page(page))
            button.pack(fill="x", padx=12, pady=3)
            self.nav_buttons[name] = button
        self.toolbar = ctk.CTkFrame(self, height=72, fg_color="#111827", corner_radius=0)
        self.toolbar.grid(row=0, column=1, sticky="ew")
        self.toolbar.grid_columnconfigure(0, weight=1)
        self.url_var = tk.StringVar(value="https://example.com")
        self.url_entry = ctk.CTkEntry(self.toolbar, textvariable=self.url_var, placeholder_text="Enter website URL")
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=16, pady=16)
        self.depth_var = tk.StringVar(value="2")
        self.limit_var = tk.StringVar(value="100")
        self.threads_var = tk.StringVar(value="10")
        for index, (label, var) in enumerate([("Depth", self.depth_var), ("Pages", self.limit_var), ("Threads", self.threads_var)], start=1):
            ctk.CTkLabel(self.toolbar, text=label).grid(row=0, column=index * 2 - 1, padx=(8, 2))
            ctk.CTkEntry(self.toolbar, textvariable=var, width=58).grid(row=0, column=index * 2, padx=(0, 8))
        ctk.CTkButton(self.toolbar, text="Start", width=80, command=self.start_crawl).grid(row=0, column=7, padx=4)
        ctk.CTkButton(self.toolbar, text="Pause", width=80, command=self.crawler.pause).grid(row=0, column=8, padx=4)
        ctk.CTkButton(self.toolbar, text="Resume", width=80, command=self.crawler.resume).grid(row=0, column=9, padx=4)
        ctk.CTkButton(self.toolbar, text="Stop", width=80, fg_color="#b91c1c", command=self.crawler.stop).grid(row=0, column=10, padx=(4, 16))
        self.content = ctk.CTkFrame(self, fg_color="#111827", corner_radius=0)
        self.content.grid(row=1, column=1, sticky="nsew")
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)
        self.status = ctk.CTkFrame(self, height=38, fg_color="#0f172a", corner_radius=0)
        self.status.grid(row=2, column=1, sticky="ew")
        self.status_label = ctk.CTkLabel(self.status, text="Ready", anchor="w")
        self.status_label.pack(side="left", padx=16)
        self.progress = ctk.CTkProgressBar(self.status, width=260)
        self.progress.pack(side="right", padx=16, pady=10)
        self.progress.set(0)

    def _build_pages(self) -> None:
        self.page_frames: dict[str, ctk.CTkFrame] = {
            "Dashboard": DashboardPage(self.content),
            "Pages": TablePage(self.content, "Pages", ["URL", "Status", "Title", "Depth", "Time", "Type", "Words"]),
            "SEO Analysis": TablePage(self.content, "SEO Analysis", ["URL", "Severity", "Issue", "Recommendation"]),
            "Images": TablePage(self.content, "Images", ["Image URL", "ALT", "Missing ALT", "Width", "Height", "Image Size"]),
            "Links": TablePage(self.content, "Links", ["URL", "Type", "Anchor Text", "Status"]),
            "Resources": TablePage(self.content, "Resources", ["Type", "URL"]),
            "Emails": TablePage(self.content, "Emails", ["Email Address"]),
            "Social Media": TablePage(self.content, "Social Media", ["Network", "URL"]),
            "Security": TablePage(self.content, "Security", ["URL", "HTTPS", "HSTS", "CSP", "X-Frame", "X-XSS", "Permissions", "Referrer", "Server"]),
            "Sitemaps": TablePage(self.content, "Sitemaps", ["Sitemap / Discovered URL"]),
            "Robots.txt": TablePage(self.content, "Robots.txt", ["Directive", "Value"]),
            "Export": ExportPage(self.content, self.export_report),
            "Settings": SettingsPage(self.content),
        }
        for frame in self.page_frames.values():
            frame.grid(row=0, column=0, sticky="nsew")

    def show_page(self, name: str) -> None:
        self.page_frames[name].tkraise()
        for page_name, button in self.nav_buttons.items():
            button.configure(fg_color="#0284c7" if page_name == name else "#1f2937")

    def start_crawl(self) -> None:
        if self.crawler.running:
            messagebox.showinfo("Crawler running", "A crawl is already in progress.")
            return
        self.pages.clear()
        self._refresh_all()
        url = self.url_var.get().strip()
        try:
            depth = max(0, int(self.depth_var.get()))
            limit = max(1, int(self.limit_var.get()))
            threads = max(1, int(self.threads_var.get()))
        except ValueError:
            messagebox.showerror("Invalid settings", "Depth, pages, and threads must be whole numbers.")
            return
        self.status_label.configure(text="Starting crawl...")
        threading.Thread(target=self._discover_site_files, args=(url,), daemon=True).start()
        self.crawler_thread = threading.Thread(target=self._run_crawler, args=(url, depth, limit, threads), daemon=True)
        self.crawler_thread.start()

    def _discover_site_files(self, url: str) -> None:
        robots_rows = self.discovery.fetch_robots(url)
        sitemap_rows = self.discovery.fetch_sitemaps(url)
        self.after(0, lambda: self._table("Robots.txt").set_rows(robots_rows))
        self.after(0, lambda: self._table("Sitemaps").set_rows(sitemap_rows))

    def _run_crawler(self, url: str, depth: int, limit: int, threads: int) -> None:
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.crawler.crawl(url, depth, limit, threads, 20, "SEO Inspector Pro/1.0", False))
        self.loop.close()

    def export_report(self, export_type: str) -> None:
        dialog = ExportProgressDialog(self, f"Export {export_type.upper()}")
        threading.Thread(target=self._run_export, args=(export_type, dialog), daemon=True).start()

    def _run_export(self, export_type: str, dialog: "ExportProgressDialog") -> None:
        sitemap_rows = self._table("Sitemaps").rows
        robots_rows = self._table("Robots.txt").rows
        failures: list[str] = []
        generated: list[Path] = []

        def progress(message: str, value: float) -> None:
            self.after(0, lambda: dialog.update_progress(message, value))

        try:
            progress("Preparing export data...", 0.05)
            if export_type == "excel":
                generated.append(self.exporter.export_excel(self.pages, sitemap_rows, robots_rows))
            elif export_type == "csv":
                generated.extend(self.exporter.export_csv(self.pages, sitemap_rows, robots_rows))
            elif export_type == "json":
                generated.append(self.exporter.export_json(self.pages, sitemap_rows, robots_rows))
            elif export_type == "html":
                generated.append(self.exporter.export_html(self.pages, sitemap_rows, robots_rows))
            elif export_type == "zip":
                zip_path, failures = self.exporter.export_zip(self.pages, sitemap_rows, robots_rows, progress)
                generated.append(zip_path)
            else:
                failures.append(f"Unknown export type: {export_type}")
            progress("Finalizing export...", 1.0)
        except Exception as exc:
            failures.append(str(exc))
        self.after(0, lambda: self._finish_export(dialog, generated, failures))

    def _finish_export(self, dialog: "ExportProgressDialog", generated: list[Path], failures: list[str]) -> None:
        dialog.destroy()
        if failures and generated:
            messagebox.showwarning("Export completed with warnings", "Generated files:\n" + "\n".join(str(path) for path in generated) + "\n\nFailed exports:\n" + "\n".join(failures))
        elif failures:
            messagebox.showerror("Export failed", "\n".join(failures))
        else:
            messagebox.showinfo("Export complete", "Generated files:\n" + "\n".join(str(path) for path in generated))

    def _receive_page_threadsafe(self, page: PageResult) -> None:
        self.after(0, lambda: self._add_page(page))

    def _receive_status_threadsafe(self, status: str) -> None:
        self.after(0, lambda: self.status_label.configure(text=status))

    def _add_page(self, page: PageResult) -> None:
        self.pages.append(page)
        self.progress.set(min(1.0, len(self.pages) / max(1, int(self.limit_var.get() or "1"))))
        self._refresh_all()

    def _refresh_all(self) -> None:
        score = self.analyzer.score(self.pages)
        dashboard = self.page_frames["Dashboard"]
        if isinstance(dashboard, DashboardPage):
            dashboard.update_metrics(self.pages, score)
        self._table("Pages").set_rows([(p.url, p.status_code, p.title, p.depth, f"{p.response_time:.2f}s", p.content_type, p.word_count) for p in self.pages])
        self._table("SEO Analysis").set_rows([(p.url, i["severity"], i["title"], i["recommendation"]) for p in self.pages for i in p.issues])
        self._table("Images").set_rows([(img.get("url", ""), img.get("alt", ""), img.get("missing_alt", ""), img.get("width", ""), img.get("height", ""), img.get("size", "")) for p in self.pages for img in p.images])
        self._table("Links").set_rows([(link.get("url", ""), link.get("type", ""), link.get("anchor", ""), link.get("status", "")) for p in self.pages for link in p.links])
        self._table("Resources").set_rows([(res.get("type", ""), res.get("url", "")) for p in self.pages for res in p.resources])
        self._table("Emails").set_rows([(email,) for email in sorted({email for p in self.pages for email in p.emails})])
        self._table("Social Media").set_rows([(network, url) for p in self.pages for network, urls in p.social_links.items() for url in urls])
        self._table("Security").set_rows([(p.url, str(p.url.startswith("https://")), p.security_headers.get("Strict-Transport-Security", ""), p.security_headers.get("Content-Security-Policy", ""), p.security_headers.get("X-Frame-Options", ""), p.security_headers.get("X-XSS-Protection", ""), p.security_headers.get("Permissions-Policy", ""), p.security_headers.get("Referrer-Policy", ""), p.security_headers.get("Server", "")) for p in self.pages])

    def _table(self, name: str) -> TablePage:
        page = self.page_frames[name]
        if not isinstance(page, TablePage):
            raise TypeError(f"{name} is not a table page")
        return page


class ExportProgressDialog(ctk.CTkToplevel):
    """Modal progress dialog used while report files are being written."""

    def __init__(self, master: MainWindow, title: str) -> None:
        super().__init__(master)
        self.title(title)
        self.geometry("420x150")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.label = ctk.CTkLabel(self, text="Preparing export...", anchor="w")
        self.label.pack(fill="x", padx=22, pady=(24, 12))
        self.progress = ctk.CTkProgressBar(self)
        self.progress.pack(fill="x", padx=22, pady=(0, 18))
        self.progress.set(0)
        ctk.CTkLabel(self, text="Please wait while SEO Inspector Pro writes the report files.", text_color="#94a3b8", wraplength=360).pack(fill="x", padx=22)

    def update_progress(self, message: str, value: float) -> None:
        self.label.configure(text=message)
        self.progress.set(max(0.0, min(1.0, value)))
