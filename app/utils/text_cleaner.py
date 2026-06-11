from __future__ import annotations

import re

from app.schemas import RawDocument


HTML_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")
EMOJI_RE = re.compile(
    "["
    "\U0001f300-\U0001f5ff"
    "\U0001f600-\U0001f64f"
    "\U0001f680-\U0001f6ff"
    "\U0001f700-\U0001f77f"
    "\U0001f780-\U0001f7ff"
    "\U0001f800-\U0001f8ff"
    "\U0001f900-\U0001f9ff"
    "\U0001fa00-\U0001fa6f"
    "\U0001fa70-\U0001faff"
    "]+",
    flags=re.UNICODE,
)
AD_KEYWORDS = ("加微信", "私信领取", "代订", "返现", "刷单", "VX", "v信")


def clean_text(text: str) -> str:
    """Remove markup, emoji, and repeated whitespace from collected text."""

    without_html = HTML_RE.sub(" ", text)
    without_emoji = EMOJI_RE.sub("", without_html)
    return SPACE_RE.sub(" ", without_emoji).strip()


def is_probable_ad(text: str) -> bool:
    """Return true when text looks like a promotion rather than travel evidence."""

    return any(keyword in text for keyword in AD_KEYWORDS)


def clean_documents(documents: list[RawDocument], min_length: int = 20) -> list[RawDocument]:
    """Clean and filter raw documents while preserving source metadata."""

    cleaned: list[RawDocument] = []
    for document in documents:
        content = clean_text(document.content)
        if len(content) < min_length or is_probable_ad(content):
            continue
        cleaned.append(document.model_copy(update={"content": content}))
    return cleaned

