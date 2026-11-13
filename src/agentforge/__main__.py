"""Punto de entrada directo para python -m agentforge."""

from __future__ import annotations

import sys

from agentforge.cli.main import run_cli


def main() -> None:
    sys.exit(run_cli())


if __name__ == "__main__":
    main()
