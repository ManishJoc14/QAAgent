"""Checks how search engines will see the site."""

from __future__ import annotations

import json
from typing import Any

from bs4 import BeautifulSoup

from ..base import BaseTool, ToolExecutionResult
from ..playwright import PlaywrightComputerTool


class SEOMetadataCheckerTool(BaseTool):
    name = "seo_metadata_checker"
    description = (
        "Check SEO-relevant metadata: titles, descriptions, headings, structured data, robots."
    )
    timeout_seconds = 20
    input_schema = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    def __init__(self, computer_tool: PlaywrightComputerTool):
        self._computer = computer_tool

    async def execute(self, arguments: dict[str, Any]) -> ToolExecutionResult:
        await self._computer.ensure_ready()

        url = arguments.get("url")
        if url:
            await self._computer.goto(url)

        findings: list[str] = []
        try:
            html_content = await self._computer.get_page_content()
            soup = BeautifulSoup(html_content, "html.parser")

            # --- Title ---
            title_tag = soup.title
            title = title_tag.string.strip() if title_tag and title_tag.string else None
            if not title:
                findings.append("Missing or empty <title> tag")

            # --- Meta description ---
            meta_desc_tag = soup.find("meta", attrs={"name": "description"})
            meta_description = meta_desc_tag.get("content", "").strip() if meta_desc_tag else None
            if not meta_description:
                findings.append("Missing or empty meta description")

            # --- Headings ---
            headings = {
                f"h{i}": [h.get_text(strip=True) for h in soup.find_all(f"h{i}")]
                for i in range(1, 7)
            }
            if not any(headings.values()):
                findings.append("No headings (<h1>-<h6>) found")

            # --- Robots meta ---
            robots_tag = soup.find("meta", attrs={"name": "robots"})
            robots_content = robots_tag.get("content", "").strip() if robots_tag else None
            if not robots_content:
                findings.append("Missing or empty robots meta tag")

            # --- Canonical link ---
            canonical_tag = soup.find("link", attrs={"rel": "canonical"})
            canonical_href = canonical_tag.get("href", "").strip() if canonical_tag else None
            if not canonical_href:
                findings.append("Missing canonical link")

            # --- JSON-LD ---
            jsonld_scripts = soup.find_all("script", type="application/ld+json")
            structured_data: list[Any] = []
            for idx, s in enumerate(jsonld_scripts):
                try:
                    structured_data.append(json.loads(s.string))
                except Exception:
                    findings.append(f"Malformed JSON-LD detected in script #{idx + 1}")

            if not findings:
                findings = ["No SEO issues detected"]

            payload = {
                "url": self._computer.current_url,
                "title": title,
                "meta_description": meta_description,
                "headings": headings,
                "robots_meta": robots_content,
                "canonical_link": canonical_href,
                "structured_data_count": len(structured_data),
                "findings": findings,
                "page_html_snippet": html_content[:5000],  # optional
            }

            return ToolExecutionResult(
                success=True,
                output=json.dumps(payload),
                metadata={"url": self._computer.current_url},
            )

        except Exception as exc:
            return ToolExecutionResult(
                success=False,
                error=f"SEO metadata parsing failed: {exc}",
                metadata={"url": self._computer.current_url},
            )
