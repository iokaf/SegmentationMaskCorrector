from src.main_window import MainWindow
from PyQt6.QtWidgets import QApplication
import sys

app = QApplication(sys.argv)
window = MainWindow("/home/yanny/Pictures/Screenshots/Screenshot from 2025-04-01 13-19-31.png")
window.show()
sys.exit(app.exec())