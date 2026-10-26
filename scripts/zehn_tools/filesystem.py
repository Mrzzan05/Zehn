from pathlib import Path


def directory_exists(path: Path) -> bool:
    return path.exists() and path.is_dir()


def file_exists(path: Path) -> bool:
    return path.exists() and path.is_file()


def missing_directories(paths: list[Path]) -> list[Path]:
    return [
        path
        for path in paths
        if not directory_exists(path)
    ]


def missing_files(paths: list[Path]) -> list[Path]:
    return [
        path
        for path in paths
        if not file_exists(path)
    ]


def create_directory(path: Path) -> None:
    path.mkdir(
        parents=True,
        exist_ok=True
    )


def create_empty_file(path: Path) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    if not path.exists():
        path.touch()