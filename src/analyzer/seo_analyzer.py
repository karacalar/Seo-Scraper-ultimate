"""SEO audit rules for crawled pages."""
from __future__ import annotations

from src.models.crawl_models import PageResult


class SEOAnalyzer:
    """Creates practical SEO issues and an aggregate score."""

    def analyze(self, page: PageResult) -> PageResult:
        issues: list[dict[str, str]] = []
        title_length = len(page.title)
        desc_length = len(page.meta_description)
        missing_alt = sum(1 for image in page.images if image.get("missing_alt"))
        broken_links = sum(1 for link in page.links if link.get("status") == "broken")

        if page.status_code >= 500:
            issues.append(self._issue("Critical", "Server error", "Fix server errors for this URL."))
        elif page.status_code == 404:
            issues.append(self._issue("Critical", "Page not found", "Restore the page or redirect it."))
        if not page.title:
            issues.append(self._issue("Critical", "Missing title", "Add a unique descriptive title tag."))
        elif title_length < 30 or title_length > 65:
            issues.append(self._issue("Warning", "Title length", "Keep title tags around 30-65 characters."))
        if not page.meta_description:
            issues.append(self._issue("Warning", "Missing meta description", "Add a compelling meta description."))
        elif desc_length < 70 or desc_length > 160:
            issues.append(self._issue("Info", "Description length", "Aim for 70-160 characters."))
        if not page.h1:
            issues.append(self._issue("Warning", "Missing H1", "Add one clear H1 heading."))
        elif len(page.h1) > 1:
            issues.append(self._issue("Info", "Multiple H1 headings", "Consider using a single primary H1."))
        if missing_alt:
            issues.append(self._issue("Warning", "Images missing ALT", f"Add ALT text to {missing_alt} image(s)."))
        if broken_links:
            issues.append(self._issue("Critical", "Broken links", f"Repair {broken_links} broken link(s)."))
        if page.response_time > 2.5:
            issues.append(self._issue("Warning", "Slow response", "Improve server response time."))
        if not page.canonical:
            issues.append(self._issue("Info", "Missing canonical", "Add a canonical URL where appropriate."))
        page.issues = issues
        return page

    def score(self, pages: list[PageResult]) -> int:
        if not pages:
            return 100
        penalty = 0
        for page in pages:
            for issue in page.issues:
                penalty += {"Critical": 10, "Warning": 5, "Info": 2}.get(issue["severity"], 1)
        return max(0, min(100, 100 - round(penalty / max(1, len(pages)))))

    @staticmethod
    def _issue(severity: str, title: str, recommendation: str) -> dict[str, str]:
        return {"severity": severity, "title": title, "recommendation": recommendation}
