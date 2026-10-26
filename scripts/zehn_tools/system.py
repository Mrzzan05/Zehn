import platform


def python_version() -> str:
    return platform.python_version()


def operating_system() -> str:
    return platform.system()