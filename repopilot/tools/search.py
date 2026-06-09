from __future__ import annotations

from pathlib import Path


def search_code(root: str | Path, query: str, limit: int = 20) -> list[tuple[str, int, str]]:
    matches: list[tuple[str, int, str]] = []
    root_path = Path(root)
    for path in root_path.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(lines, start=1):
            if query.lower() in line.lower():
                matches.append((str(path.relative_to(root_path)), line_number, line))
                if len(matches) >= limit:
                    return matches
    return matches

