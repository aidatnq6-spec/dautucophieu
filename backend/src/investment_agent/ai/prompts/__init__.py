"""Versioned prompt texts; the first line declares the version recorded with every run."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Prompt:
    version: str
    text: str


def load_prompt(name: str) -> Prompt:
    lines = (Path(__file__).parent / f"{name}.vi.txt").read_text(encoding="utf-8").splitlines()
    header = lines[0].removeprefix("# prompt-version:").strip()
    if not lines[0].startswith("# prompt-version:") or not header:
        raise ValueError("prompt file needs a version header")
    return Prompt(version=header, text="\n".join(lines[1:]).strip())
