from zehn_tools.config import (
    REQUIRED_DOCS,
    REQUIRED_DIRECTORIES,
)

from zehn_tools.filesystem import (
    missing_directories,
    missing_files,
    create_directory,
    create_empty_file,
)

from zehn_tools.reporting import (
    print_header,
    print_success,
    print_warning,
)


def initialize_directories():
    missing = missing_directories(
        REQUIRED_DIRECTORIES
    )

    if not missing:
        print_success(
            "All required directories exist."
        )
        return

    for directory in missing:
        create_directory(directory)
        print_success(
            f"Created directory: {directory}"
        )


def initialize_files():
    missing = missing_files(
        REQUIRED_DOCS
    )

    if not missing:
        print_success(
            "All required documentation files exist."
        )
        return

    for file in missing:
        create_empty_file(file)

        print_warning(
            f"Created missing file: {file}"
        )


def main():

    print_header(
        "Zehn Documentation Initializer"
    )

    initialize_directories()

    initialize_files()

    print()
    print_success(
        "Documentation structure validation completed."
    )


if __name__ == "__main__":
    main()