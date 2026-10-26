from zehn_tools.config import (
    DOCS_DIR,
    CONTEXT_DIR,
)

from zehn_tools.context import (
    read_file,
    build_document,
)


GENERATED_DIR = (
    CONTEXT_DIR
    /
    "generated"
)


CONTEXTS = {

    "full_context.md": [

        (
            "Project Identity",
            DOCS_DIR / "00_PROJECT.md",
        ),

        (
            "Architecture",
            DOCS_DIR / "01_ARCHITECTURE.md",
        ),

        (
            "Decisions",
            DOCS_DIR / "02_DECISIONS.md",
        ),

        (
            "Glossary",
            DOCS_DIR / "05_GLOSSARY.md",
        ),

        (
            "AI Context",
            DOCS_DIR / "06_AI_CONTEXT.md",
        ),

    ],


    "architecture_context.md": [

        (
            "Architecture",
            DOCS_DIR / "01_ARCHITECTURE.md",
        ),

        (
            "Decisions",
            DOCS_DIR / "02_DECISIONS.md",
        ),

        (
            "Glossary",
            DOCS_DIR / "05_GLOSSARY.md",
        ),

    ],


    "extraction_context.md": [

        (
            "Architecture",
            DOCS_DIR / "01_ARCHITECTURE.md",
        ),

        (
            "Glossary",
            DOCS_DIR / "05_GLOSSARY.md",
        ),

    ],


    "task_context.md": [

        (
            "Next Task",
            DOCS_DIR / "07_NEXT_TASK.md",
        ),

        (
            "Architecture",
            DOCS_DIR / "01_ARCHITECTURE.md",
        ),

    ],

}


def build_context(
    filename,
    sources
):

    sections = []

    for title, path in sources:

        content = read_file(path)

        if content:

            sections.append(
                (
                    title,
                    content,
                )
            )


    output = build_document(
        sections
    )


    target = (
        GENERATED_DIR
        /
        filename
    )


    target.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    target.write_text(
        output,
        encoding="utf-8"
    )


    print(
        f"Generated: {target}"
    )


def main():

    for filename, sources in CONTEXTS.items():

        build_context(
            filename,
            sources
        )


if __name__ == "__main__":
    main()