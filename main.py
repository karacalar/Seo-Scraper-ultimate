"""Application entry point for SEO Inspector Pro."""
from __future__ import annotations

from src.ui.main_window import MainWindow
from src.utils.logging_config import configure_logging


def main() -> None:
    """Launch the desktop application."""
    configure_logging()
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
