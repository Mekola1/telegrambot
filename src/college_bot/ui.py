from __future__ import annotations

from html import escape


LINE = "------------------------------"


def h(value: object) -> str:
    return escape("" if value is None else str(value))


def title(text: str) -> str:
    return f"<b>{h(text)}</b>"


def section(text: str) -> str:
    return f"\n{LINE}\n<b>{h(text)}</b>"


def field(label: str, value: object) -> str:
    return f"<b>{h(label)}:</b> {h(value)}"


def muted(value: object) -> str:
    return h(value or "не вказано")


def intro_panel(title_text: str, body: str) -> str:
    return f"{title(title_text)}\n\n{body}"
