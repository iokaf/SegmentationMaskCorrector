import sys
import yaml

from PyQt6.QtWidgets import QApplication

from src.main_window import MainWindow

config = yaml.safe_load(open("config.yaml"))

app = QApplication(sys.argv)
window = MainWindow(config)
window.show()
sys.exit(app.exec())