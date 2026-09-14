"""AWS documentation HTML → Markdown.

docs.aws.amazon.com pages are server-rendered; the article lives in ``#main-col-body``.
Everything else (nav, breadcrumbs, feedback widgets, "Did this page help you?") is chrome.
"""

from bs4 import BeautifulSoup, Tag
from markdownify import MarkdownConverter

_CHROME_SELECTORS = (
    "script",
    "style",
    "noscript",
    "nav",
    "header",
    "footer",
    ".awsdocs-page-utilities",
    ".awsdocs-copy-button",
    ".awsdocs-view-content",
    ".awsdocs-filter-selector",
    "#main-col-footer",
    ".prev-next",
    ".awsdocs-feedback",
    "awsdocs-copy-clipboard",
    "awsdocs-view",
    "awsui-alert.awsdocs-page-banner",
    "awsdocs-language-banner",
    ".code-btn-container",
    ".btn-copy-code",
)


class _AwsConverter(MarkdownConverter):
    """ATX headings, fenced code, and no image noise."""

    def convert_img(self, el: Tag, text: str, parent_tags: set[str]) -> str:
        alt = el.get("alt") or ""
        return f"[image: {alt}]" if alt else ""

    def convert_pre(self, el: Tag, text: str, parent_tags: set[str]) -> str:
        code = el.get_text()
        return f"\n```\n{code.rstrip()}\n```\n"


def parse_aws_html(raw: str) -> str:
    soup = BeautifulSoup(raw, "html.parser")
    body = soup.select_one("#main-col-body") or soup.body or soup
    for sel in _CHROME_SELECTORS:
        for node in body.select(sel):
            node.decompose()
    # AWS wraps the page title in <h1 class="topictitle">; markdownify handles it as H1.
    md: str = _AwsConverter(heading_style="ATX", bullets="-").convert_soup(body)
    lines = [ln.rstrip() for ln in md.replace("\xa0", " ").splitlines()]
    out: list[str] = []
    blank = 0
    for ln in lines:
        blank = blank + 1 if not ln.strip() else 0
        if blank <= 2:
            out.append(ln)
    return "\n".join(out).strip() + "\n"
