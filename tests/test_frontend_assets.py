from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_ROOT = PROJECT_ROOT / "frontend"


class AssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.references: list[str] = []

    def handle_starttag(self, _tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name in {"href", "src"} and value:
                self.references.append(value)


def test_static_frontend_pages_reference_existing_local_assets():
    pages = sorted(FRONTEND_ROOT.glob("*.html"))
    assert {page.name for page in pages} >= {
        "index.html",
        "explorer.html",
        "pricing.html",
        "about.html",
        "purchase-complete.html",
        "404.html",
    }

    missing: list[str] = []
    for page in pages:
        parser = AssetParser()
        parser.feed(page.read_text(encoding="utf-8"))
        for reference in parser.references:
            parsed = urlparse(reference)
            if parsed.scheme or reference.startswith(("#", "mailto:")):
                continue
            path = parsed.path
            if path in {"", "/"} or path.startswith("/api/"):
                continue
            candidate = FRONTEND_ROOT / path.lstrip("/")
            if not candidate.exists():
                missing.append(f"{page.name}: {reference}")

    assert missing == []


def test_public_javascript_does_not_embed_secret_credentials():
    javascript = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((FRONTEND_ROOT / "assets" / "js").glob("*.js"))
    )
    for forbidden in ("sk_live_", "sk_test_", "AWS_SECRET_ACCESS_KEY", "AKIA"):
        assert forbidden not in javascript
