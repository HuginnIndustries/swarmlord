"""Custom Jinja2 filters used in prompt templates."""

from __future__ import annotations


def trim_filter(value: object) -> str:
    """Strip leading/trailing whitespace from any stringifiable value."""
    return ("" if value is None else str(value)).strip()


def indent_filter(value: object, n: int = 2) -> str:
    """Indent every non-empty line of ``value`` by ``n`` spaces."""
    if value is None:
        return ""
    pad = " " * n
    text = str(value)
    return "\n".join(f"{pad}{line}" if line else line for line in text.splitlines())


def default_empty(value: object, fallback: str = "") -> str:
    """Return ``fallback`` if ``value`` is falsy, else ``str(value)``."""
    return str(value) if value else fallback


def summarize(value: object, n_words: int = 25) -> str:
    """Truncate ``value`` to ``n_words`` words, appending an ellipsis if cut."""
    if value is None:
        return ""
    words = str(value).split()
    if len(words) <= n_words:
        return " ".join(words)
    return " ".join(words[:n_words]) + "..."
