import sys

from PySide6.QtWidgets import QApplication

import database
from ui.main_window import MainWindow


def main():
    database.init_db()

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
