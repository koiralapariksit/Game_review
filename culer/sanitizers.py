"""
Reusable HTML sanitization utilities for user-submitted content.
Uses nh3 (Ammonia-based fast and secure HTML sanitizer).
"""
import nh3

SAFE_RICH_TAGS = {
    'b', 'i', 'strong', 'em', 'p', 'br',
    'ul', 'ol', 'li', 'blockquote', 'code'
}


def sanitize_plain_text(value: str) -> str:
    """
    Strips ALL HTML tags from the input string, returning pure plain text.
    Used for titles, names, short descriptions, and plaintext inputs.
    """
    if not value:
        return ''
    if not isinstance(value, str):
        value = str(value)
    return nh3.clean(value, tags=set())


def sanitize_rich_text(value: str) -> str:
    """
    Permits only safe formatting tags:
    ('b', 'i', 'strong', 'em', 'p', 'br', 'ul', 'ol', 'li', 'blockquote', 'code')
    and completely strips scripts, styles, event handlers (onerror, onload, etc.),
    and unsafe attributes.
    """
    if not value:
        return ''
    if not isinstance(value, str):
        value = str(value)
    return nh3.clean(
        value,
        tags=SAFE_RICH_TAGS,
        attributes={},
        strip_comments=True
    )

