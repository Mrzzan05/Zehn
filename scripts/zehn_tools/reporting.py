def print_header(title: str):

    print()
    print("=" * 60)
    print(title)
    print("=" * 60)
    print()


def print_success(message: str):

    print(f"[OK] {message}")


def print_warning(message: str):

    print(f"[WARNING] {message}")


def print_error(message: str):

    print(f"[ERROR] {message}")