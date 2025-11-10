# support running as `python -m importlinter`
from .cli import lint_imports_command

if __name__ == "__main__":
    lint_imports_command()
