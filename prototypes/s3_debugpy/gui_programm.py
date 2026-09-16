"""S3: minimales GUI-Programm für den debugpy-Test.

Siehe prototypes/s3_debugpy/README.md.
"""

import sys

from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QWidget


class Fenster(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("S3 – GUI-Programm")
        self.klicks = 0

        self.beschriftung = QLabel("0 Klicks")
        knopf = QPushButton("Klicken")
        knopf.clicked.connect(self.button_geklickt)

        layout = QVBoxLayout(self)
        layout.addWidget(self.beschriftung)
        layout.addWidget(knopf)

    def button_geklickt(self) -> None:
        self.klicks += 1  # <- hier Breakpoint setzen
        self.beschriftung.setText(f"{self.klicks} Klicks")


def main() -> None:
    app = QApplication(sys.argv)
    fenster = Fenster()
    fenster.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
