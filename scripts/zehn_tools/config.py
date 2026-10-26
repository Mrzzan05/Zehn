from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


DOCS_DIR = PROJECT_ROOT / "docs"

SCRIPTS_DIR = PROJECT_ROOT / "scripts"

CONTEXT_DIR = PROJECT_ROOT / "context"


REQUIRED_DOCS = [
    DOCS_DIR / "00_PROJECT.md",
    DOCS_DIR / "01_ARCHITECTURE.md",
    DOCS_DIR / "02_DECISIONS.md",
    DOCS_DIR / "03_STATUS.md",
    DOCS_DIR / "04_ROADMAP.md",
    DOCS_DIR / "05_GLOSSARY.md",
    DOCS_DIR / "06_AI_CONTEXT.md",
    DOCS_DIR / "07_NEXT_TASK.md",
]


REQUIRED_DIRECTORIES = [
    DOCS_DIR,
    DOCS_DIR / "adr",
    DOCS_DIR / "rfc",
    DOCS_DIR / "milestones",
    DOCS_DIR / "knowledge",
    DOCS_DIR / "templates",
    CONTEXT_DIR,
]


STATUS_FILE = DOCS_DIR / "03_STATUS.md"

AI_CONTEXT_FILE = DOCS_DIR / "06_AI_CONTEXT.md"