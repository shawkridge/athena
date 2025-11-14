"""Athena CLI entry point for module execution.

Allows running: python3 -m athena.cli <command> <args>
"""

import sys
from .main import main

if __name__ == "__main__":
    sys.exit(main())
