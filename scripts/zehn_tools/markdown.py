from pathlib import Path


def read_markdown(path: Path) -> str:

    if not path.exists():
        return ""

    return path.read_text(
        encoding="utf-8"
    )


def write_markdown(
    path: Path,
    content: str
) -> None:

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    path.write_text(
        content,
        encoding="utf-8"
    )