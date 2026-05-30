"""Entry point for the HSE Schedule Parser TUI wizard.

Usage:
    python -m hse_schedule_parser
"""

from hse_schedule_parser.wizard import run_wizard


def main() -> None:
    """Run the interactive TUI wizard."""
    run_wizard()


if __name__ == "__main__":
    main()