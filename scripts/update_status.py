from datetime import datetime, timezone

from zehn_tools.config import (
    PROJECT_ROOT,
    STATUS_FILE,
)

from zehn_tools.git import (
    current_branch,
    current_commit,
    git_status,
)

from zehn_tools.markdown import (
    write_markdown,
)

from zehn_tools.system import (
    python_version,
    operating_system,
)


def collect_status() -> dict:

    return {
        "updated":
            datetime.now(timezone.utc)
            .strftime("%Y-%m-%d %H:%M:%S UTC"),

        "branch":
            current_branch(PROJECT_ROOT),

        "commit":
            current_commit(PROJECT_ROOT),

        "git_status":
            git_status(PROJECT_ROOT),

        "python":
            python_version(),

        "os":
            operating_system(),
    }


def render_status(data: dict) -> str:

    git_state = (
        data["git_status"]
        if data["git_status"]
        else "Clean working tree"
    )

    return f"""# Project Status

> AUTO GENERATED FILE

Do not edit manually.

---

# Last Updated

{data["updated"]}

---

# Repository

## Branch

{data["branch"]}

## Commit

{data["commit"]}

## Working Tree

{git_state}

---

# Environment

## Python

{data["python"]}

## Operating System

{data["os"]}

---

# Current Milestone

Reality Core Stabilization

---

# Current Objective

Continue stabilizing the Reality Core architecture.

---

# Tests

Not collected yet.

(Test integration will be added in future versions.)

---

# Known Risks

No automatic analysis available.

---

# Blockers

None detected.

---

# Next Task

See:

docs/07_NEXT_TASK.md
"""


def main():

    status = collect_status()

    content = render_status(status)

    write_markdown(
        STATUS_FILE,
        content
    )

    print(
        "Project status updated successfully."
    )


if __name__ == "__main__":
    main()