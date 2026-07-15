"""Small, deterministic builder for plain-text operational reports."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass
class PlaintextReport:
    title: str
    underline: str = "="
    _lines: list[str] = field(default_factory=list)

    def line(self, text: object = "") -> "PlaintextReport":
        self._lines.append(str(text))
        return self

    def lines(self, values: Iterable[object]) -> "PlaintextReport":
        self._lines.extend(str(value) for value in values)
        return self

    def blank(self) -> "PlaintextReport":
        self._lines.append("")
        return self

    def section(self, title: str) -> "PlaintextReport":
        if self._lines and self._lines[-1] != "":
            self._lines.append("")
        self._lines.extend((title, "-" * len(title)))
        return self

    def render(self) -> str:
        lines = [self.title, self.underline * len(self.title), "", *self._lines]
        return "\n".join(lines).rstrip() + "\n"
