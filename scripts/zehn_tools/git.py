import subprocess
from pathlib import Path


def run_git_command(
    root: Path,
    command: list[str]
) -> str:

    result = subprocess.run(
        ["git", *command],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return ""

    return result.stdout.strip()


def current_branch(root: Path) -> str:
    return run_git_command(
        root,
        ["branch", "--show-current"]
    )


def current_commit(root: Path) -> str:
    return run_git_command(
        root,
        ["rev-parse", "--short", "HEAD"]
    )


def git_status(root: Path) -> str:
    return run_git_command(
        root,
        ["status", "--short"]
    )