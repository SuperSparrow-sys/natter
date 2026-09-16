"""S5: minimales Schülerprogramm für den PyInstaller-Test (PySide6 + pandas).

Siehe prototypes/s5_pyinstaller/README.md.
"""

import sys

import pandas as pd
from PySide6.QtWidgets import QApplication, QLabel


def main() -> None:
    app = QApplication(sys.argv)
    df = pd.DataFrame({"name": ["Rot", "Gelb", "Grün"], "wert": [1, 2, 3]})
    beschriftung = QLabel(f"pandas funktioniert:\n{df.to_string(index=False)}")
    beschriftung.setWindowTitle("S5 – PyInstaller-Test")
    beschriftung.resize(300, 150)
    beschriftung.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
