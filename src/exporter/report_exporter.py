"""Production export services for SEO Inspector Pro reports."""
from __future__ import annotations

import csv
import json
import zipfile
from html import escape
from dataclasses import asdict, is_dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Callable
from uuid import UUID


from src.analyzer.seo_analyzer import SEOAnalyzer
from src.models.crawl_models import PageResult

ProgressCallback = Callable[[str, float], None]


class ReportJSONEncoder(json.JSONEncoder):
    """JSON encoder that supports common application and Python value types."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Path):
            return str(obj)
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, set):
            return sorted(obj, key=str)
        if is_dataclass(obj):
            return asdict(obj)
        return str(obj)


class ReportExporter:
    """Exports crawl results to Excel, CSV, JSON, HTML, and ZIP formats."""

    def __init__(self, output_dir: Path | str = "reports") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.analyzer = SEOAnalyzer()

    def export_excel(self, pages: list[PageResult], sitemap_rows: list[tuple[Any, ...]], robots_rows: list[tuple[Any, ...]]) -> Path:
        path = self.output_dir / "SEO_Report.xlsx"
        sections = self.build_sections(pages, sitemap_rows, robots_rows)
        workbook_data = {name: sections[name] for name in ["Summary", "Pages", "SEO Analysis", "Images", "Links", "Resources", "Emails", "Social Media", "Security"]}
        self._write_xlsx(path, workbook_data)
        return path

    def export_csv(self, pages: list[PageResult], sitemap_rows: list[tuple[Any, ...]], robots_rows: list[tuple[Any, ...]]) -> list[Path]:
        sections = self.build_sections(pages, sitemap_rows, robots_rows)
        mapping = {
            "Pages.csv": sections["Pages"],
            "SEO.csv": sections["SEO Analysis"],
            "Images.csv": sections["Images"],
            "Links.csv": sections["Links"],
            "Resources.csv": sections["Resources"],
            "Emails.csv": sections["Emails"],
            "Security.csv": sections["Security"],
            "Social.csv": sections["Social Media"],
            "Sitemap.csv": sections["Sitemap"],
            "Robots.csv": sections["Robots.txt"],
        }
        paths: list[Path] = []
        for filename, rows in mapping.items():
            path = self.output_dir / filename
            self._write_csv(path, rows)
            paths.append(path)
        return paths

    def export_json(self, pages: list[PageResult], sitemap_rows: list[tuple[Any, ...]], robots_rows: list[tuple[Any, ...]]) -> Path:
        path = self.output_dir / "Report.json"
        data = {
            "generated_at": datetime.now(timezone.utc),
            "sections": self.build_sections(pages, sitemap_rows, robots_rows),
            "raw_pages": pages,
        }
        path.write_text(json.dumps(data, cls=ReportJSONEncoder, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def export_html(self, pages: list[PageResult], sitemap_rows: list[tuple[Any, ...]], robots_rows: list[tuple[Any, ...]]) -> Path:
        path = self.output_dir / "SEO_Report.html"
        sections = self.build_sections(pages, sitemap_rows, robots_rows)
        html = self._render_html(sections, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        path.write_text(html, encoding="utf-8")
        return path

    def export_zip(self, pages: list[PageResult], sitemap_rows: list[tuple[Any, ...]], robots_rows: list[tuple[Any, ...]], progress: ProgressCallback | None = None) -> tuple[Path, list[str]]:
        failures: list[str] = []
        steps = [
            ("Excel", lambda: self.export_excel(pages, sitemap_rows, robots_rows)),
            ("CSV", lambda: self.export_csv(pages, sitemap_rows, robots_rows)),
            ("JSON", lambda: self.export_json(pages, sitemap_rows, robots_rows)),
            ("HTML", lambda: self.export_html(pages, sitemap_rows, robots_rows)),
        ]
        generated: list[Path] = []
        for index, (name, action) in enumerate(steps, start=1):
            if progress:
                progress(f"Exporting {name}...", (index - 1) / (len(steps) + 1))
            try:
                result = action()
                generated.extend(result if isinstance(result, list) else [result])
            except Exception as exc:
                failures.append(f"{name}: {exc}")
        zip_path = self.output_dir / "SEO_Report.zip"
        if progress:
            progress("Creating ZIP package...", len(steps) / (len(steps) + 1))
        if zip_path.exists():
            zip_path.unlink()
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for file_path in generated:
                if file_path.exists() and file_path != zip_path:
                    archive.write(file_path, file_path.name)
        if progress:
            progress("Export complete.", 1.0)
        return zip_path, failures

    def build_sections(self, pages: list[PageResult], sitemap_rows: list[tuple[Any, ...]], robots_rows: list[tuple[Any, ...]]) -> dict[str, list[dict[str, Any]]]:
        score = self.analyzer.score(pages)
        status_counts: dict[int, int] = {}
        for page in pages:
            status_counts[page.status_code] = status_counts.get(page.status_code, 0) + 1
        internal_links = sum(1 for page in pages for link in page.links if link.get("type") == "internal")
        external_links = sum(1 for page in pages for link in page.links if link.get("type") == "external")
        images = sum(len(page.images) for page in pages)
        broken_links = sum(1 for page in pages for link in page.links if link.get("status") == "broken")
        average_response = sum(page.response_time for page in pages) / max(1, len(pages))
        issue_summary: dict[str, int] = {"Critical": 0, "Warning": 0, "Info": 0}
        for page in pages:
            for issue in page.issues:
                severity = issue.get("severity", "Info")
                issue_summary[severity] = issue_summary.get(severity, 0) + 1
        return {
            "Summary": [
                {"Metric": "Total Pages", "Value": len(pages)},
                {"Metric": "Internal Links", "Value": internal_links},
                {"Metric": "External Links", "Value": external_links},
                {"Metric": "Images", "Value": images},
                {"Metric": "Broken Links", "Value": broken_links},
                {"Metric": "SEO Score", "Value": score},
                {"Metric": "Average Response Time", "Value": round(average_response, 3)},
                *[{"Metric": f"HTTP {code}", "Value": count} for code, count in sorted(status_counts.items())],
                *[{"Metric": f"{severity} Issues", "Value": count} for severity, count in issue_summary.items()],
            ],
            "Pages": [{"URL": p.url, "Status Code": p.status_code, "Title": p.title, "Depth": p.depth, "Response Time": p.response_time, "Content Type": p.content_type, "Word Count": p.word_count, "Error": p.error} for p in pages],
            "SEO Analysis": [{"URL": p.url, "Severity": i.get("severity", ""), "Issue": i.get("title", ""), "Recommendation": i.get("recommendation", ""), "Title": p.title, "Title Length": len(p.title), "Meta Description": p.meta_description, "Description Length": len(p.meta_description), "H1": " | ".join(p.h1), "H2": " | ".join(p.h2), "Canonical": p.canonical, "Meta Robots": p.meta_robots, "Open Graph": p.open_graph, "Twitter Cards": p.twitter_cards, "Structured Data": p.structured_data, "Word Count": p.word_count, "Images": len(p.images), "Missing ALT": sum(1 for img in p.images if img.get("missing_alt")), "Internal Links": sum(1 for link in p.links if link.get("type") == "internal"), "External Links": sum(1 for link in p.links if link.get("type") == "external"), "Response Time": p.response_time, "Status Code": p.status_code} for p in pages for i in (p.issues or [{"severity": "Info", "title": "No SEO issues", "recommendation": "No action required."}])],
            "Images": [{"Page URL": p.url, "Image URL": img.get("url", ""), "ALT": img.get("alt", ""), "Missing ALT": img.get("missing_alt", ""), "Width": img.get("width", ""), "Height": img.get("height", ""), "Image Size": img.get("size", "")} for p in pages for img in p.images],
            "Links": [{"Page URL": p.url, "Link URL": link.get("url", ""), "Type": link.get("type", ""), "Anchor Text": link.get("anchor", ""), "Status": link.get("status", "")} for p in pages for link in p.links],
            "Resources": [{"Page URL": p.url, "Type": resource.get("type", ""), "URL": resource.get("url", "")} for p in pages for resource in p.resources],
            "Emails": [{"Email Address": email} for email in sorted({email for p in pages for email in p.emails})],
            "Social Media": [{"Network": network, "URL": url} for p in pages for network, urls in p.social_links.items() for url in sorted(urls)],
            "Security": [{"URL": p.url, "HTTPS": p.url.startswith("https://"), "HSTS": p.security_headers.get("Strict-Transport-Security", ""), "Content Security Policy": p.security_headers.get("Content-Security-Policy", ""), "X-Frame-Options": p.security_headers.get("X-Frame-Options", ""), "X-XSS-Protection": p.security_headers.get("X-XSS-Protection", ""), "Permissions Policy": p.security_headers.get("Permissions-Policy", ""), "Referrer Policy": p.security_headers.get("Referrer-Policy", ""), "Server Header": p.security_headers.get("Server", "")} for p in pages],
            "Sitemap": [{"Sitemap / Discovered URL": row[0] if row else ""} for row in sitemap_rows],
            "Robots.txt": [{"Directive": row[0] if len(row) > 0 else "", "Value": row[1] if len(row) > 1 else ""} for row in robots_rows],
            "Status Distribution": [{"Status Code": code, "Count": count} for code, count in sorted(status_counts.items())],
            "Issue Summary": [{"Severity": severity, "Count": count} for severity, count in issue_summary.items()],
        }

    def _write_csv(self, path: Path, rows: list[dict[str, Any]]) -> None:
        fieldnames = list(rows[0].keys()) if rows else ["No Data"]
        with path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            if rows:
                writer.writerows([{key: self._stringify(value) for key, value in row.items()} for row in rows])

    def _write_xlsx(self, path: Path, worksheets: dict[str, list[dict[str, Any]]]) -> None:
        sheet_names = list(worksheets)
        workbook_xml = "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><workbook xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\" xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\"><sheets>"
        workbook_xml += "".join(f"<sheet name=\"{escape(name[:31])}\" sheetId=\"{index}\" r:id=\"rId{index}\"/>" for index, name in enumerate(sheet_names, start=1))
        workbook_xml += "</sheets></workbook>"
        rels = "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
        rels += "<Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"xl/workbook.xml\"/></Relationships>"
        workbook_rels = "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
        workbook_rels += "".join(f"<Relationship Id=\"rId{index}\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet\" Target=\"worksheets/sheet{index}.xml\"/>" for index in range(1, len(sheet_names) + 1))
        workbook_rels += "</Relationships>"
        content_types = "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\"><Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/><Default Extension=\"xml\" ContentType=\"application/xml\"/><Override PartName=\"/xl/workbook.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml\"/>"
        content_types += "".join(f"<Override PartName=\"/xl/worksheets/sheet{index}.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml\"/>" for index in range(1, len(sheet_names) + 1))
        content_types += "</Types>"
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as workbook:
            workbook.writestr("[Content_Types].xml", content_types)
            workbook.writestr("_rels/.rels", rels)
            workbook.writestr("xl/workbook.xml", workbook_xml)
            workbook.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
            for index, name in enumerate(sheet_names, start=1):
                workbook.writestr(f"xl/worksheets/sheet{index}.xml", self._worksheet_xml(worksheets[name]))

    def _worksheet_xml(self, rows: list[dict[str, Any]]) -> str:
        headers = list(rows[0].keys()) if rows else ["No Data"]
        table_rows = [headers, *[[self._stringify(row.get(header, "")) for header in headers] for row in rows]]
        xml_rows = []
        for row_index, values in enumerate(table_rows, start=1):
            cells = []
            for column_index, value in enumerate(values, start=1):
                cell_ref = f"{self._column_name(column_index)}{row_index}"
                cells.append(f"<c r=\"{cell_ref}\" t=\"inlineStr\"><is><t>{escape(str(value))}</t></is></c>")
            xml_rows.append(f"<row r=\"{row_index}\">{''.join(cells)}</row>")
        return "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><worksheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\"><sheetData>" + "".join(xml_rows) + "</sheetData></worksheet>"

    @staticmethod
    def _column_name(index: int) -> str:
        name = ""
        while index:
            index, remainder = divmod(index - 1, 26)
            name = chr(65 + remainder) + name
        return name

    def _render_html(self, sections: dict[str, list[dict[str, Any]]], generated_at: str) -> str:
        summary = sections["Summary"]
        score = summary[5]["Value"] if len(summary) > 5 else 0
        max_status = max([row["Count"] for row in sections["Status Distribution"]] or [1])
        max_issue = max([row["Count"] for row in sections["Issue Summary"]] or [1])
        metric_cards = "".join(f"<div class='card'><div class='label'>{escape(str(item['Metric']))}</div><div class='metric'>{escape(str(item['Value']))}</div></div>" for item in summary[:7])
        status_rows = "".join(f"<div class='chart-row'><span>HTTP {escape(str(row['Status Code']))}</span><div class='bar'><div class='fill' style='width:{(row['Count'] / max_status * 100):.0f}%'></div></div><strong>{row['Count']}</strong></div>" for row in sections["Status Distribution"])
        issue_rows = "".join(f"<div class='chart-row'><span class='{escape(str(row['Severity']).lower())}'>{escape(str(row['Severity']))}</span><div class='bar'><div class='fill' style='width:{(row['Count'] / max_issue * 100):.0f}%'></div></div><strong>{row['Count']}</strong></div>" for row in sections["Issue Summary"])
        recommendation_rows = "".join(f"<tr><td>{escape(str(row['URL']))}</td><td class='{escape(str(row['Severity']).lower())}'>{escape(str(row['Severity']))}</td><td>{escape(str(row['Issue']))}</td><td>{escape(str(row['Recommendation']))}</td></tr>" for row in sections["SEO Analysis"][:100])
        page_rows = "".join(f"<tr><td>{escape(str(row['URL']))}</td><td>{escape(str(row['Status Code']))}</td><td>{escape(str(row['Title']))}</td><td>{escape(str(row['Depth']))}</td><td>{escape(str(row['Response Time']))}</td><td>{escape(str(row['Word Count']))}</td></tr>" for row in sections["Pages"][:100])
        sitemap_rows = "".join(f"<tr><td>{escape(str(row['Sitemap / Discovered URL']))}</td></tr>" for row in sections["Sitemap"][:50])
        robots_rows = "".join(f"<tr><td>{escape(str(row['Directive']))}</td><td>{escape(str(row['Value']))}</td></tr>" for row in sections["Robots.txt"][:80])
        return HTML_TEMPLATE.format(generated_at=escape(generated_at), score=score, metric_cards=metric_cards, status_rows=status_rows, issue_rows=issue_rows, recommendation_rows=recommendation_rows, page_rows=page_rows, sitemap_rows=sitemap_rows, robots_rows=robots_rows)

    @staticmethod
    def _stringify(value: Any) -> str:
        return json.dumps(value, cls=ReportJSONEncoder, ensure_ascii=False) if isinstance(value, (dict, list, set, tuple)) else str(value)


HTML_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SEO Inspector Pro Report</title>
<style>
:root{{color-scheme:dark;--bg:#0f172a;--panel:#111827;--card:#1f2937;--text:#e5e7eb;--muted:#94a3b8;--accent:#38bdf8;--critical:#ef4444;--warning:#f59e0b;--info:#60a5fa;--ok:#22c55e}}*{{box-sizing:border-box}}body{{margin:0;background:linear-gradient(135deg,#020617,#111827);color:var(--text);font-family:Segoe UI,Roboto,Arial,sans-serif}}.wrap{{max-width:1280px;margin:auto;padding:32px}}.hero{{display:flex;justify-content:space-between;gap:24px;align-items:flex-start;margin-bottom:24px}}.eyebrow{{color:var(--accent);font-weight:700;text-transform:uppercase;letter-spacing:.12em}}h1{{font-size:40px;margin:.2rem 0}}.card{{background:rgba(31,41,55,.88);border:1px solid rgba(148,163,184,.18);border-radius:18px;padding:20px;box-shadow:0 18px 50px rgba(0,0,0,.25)}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px}}.metric{{font-size:30px;font-weight:800}}.label{{color:var(--muted);font-size:13px}}.score{{font-size:56px;color:var(--ok);font-weight:900}}.bar{{height:14px;background:#334155;border-radius:999px;overflow:hidden}}.fill{{height:100%;background:linear-gradient(90deg,var(--accent),var(--ok))}}.chart-row{{display:grid;grid-template-columns:100px 1fr 60px;gap:12px;align-items:center;margin:10px 0}}.critical{{color:var(--critical)}}.warning{{color:var(--warning)}}.info{{color:var(--info)}}table{{border-collapse:collapse;width:100%;margin-top:12px}}th,td{{padding:10px 12px;border-bottom:1px solid rgba(148,163,184,.16);text-align:left;vertical-align:top}}th{{color:var(--accent);font-size:13px}}td{{font-size:13px;color:#d1d5db}}.section{{margin:22px 0}}@media(max-width:760px){{.hero{{display:block}}.wrap{{padding:18px}}h1{{font-size:30px}}}}
</style>
</head>
<body><main class="wrap">
<section class="hero"><div><div class="eyebrow">SEO Inspector Pro</div><h1>Professional SEO Audit Report</h1><p class="label">Generated {generated_at}</p></div><div class="card"><div class="label">SEO Score</div><div class="score">{score}/100</div><div class="bar"><div class="fill" style="width:{score}%"></div></div></div></section>
<section class="grid section">{metric_cards}</section>
<section class="grid section"><div class="card"><h2>Status Code Distribution</h2>{status_rows}</div><div class="card"><h2>Issue Summary</h2>{issue_rows}</div></section>
<section class="card section"><h2>Recommendations</h2><table><thead><tr><th>URL</th><th>Severity</th><th>Issue</th><th>Recommendation</th></tr></thead><tbody>{recommendation_rows}</tbody></table></section>
<section class="card section"><h2>Pages</h2><table><thead><tr><th>URL</th><th>Status</th><th>Title</th><th>Depth</th><th>Response Time</th><th>Words</th></tr></thead><tbody>{page_rows}</tbody></table></section>
<section class="grid section"><div class="card"><h2>Sitemaps</h2><table><tbody>{sitemap_rows}</tbody></table></div><div class="card"><h2>Robots.txt</h2><table><tbody>{robots_rows}</tbody></table></div></section>
</main></body></html>
"""
