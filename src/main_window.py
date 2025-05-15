import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QFileDialog, QMessageBox,
    QLabel, QScrollArea
)
from PySide6.QtCore import Qt

from src.components import MaskPainter

class MainWindow(QWidget):
    def __init__(self, image_path):
        super().__init__()

        self.setWindowTitle("Semantic Segmentation Annotation")

        self.canvas = MaskPainter(image_path)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.canvas)

        self.label_selector = QComboBox()
        default_labels = ["Background", "Object1", "Object2"]
        self.label_selector.addItems(default_labels)
        self.label_selector.currentTextChanged.connect(self.change_label)
        self.canvas.set_active_label(default_labels[0])

        self.draw_btn = QPushButton("Draw")
        self.erase_btn = QPushButton("Erase")
        self.undo_btn = QPushButton("Undo")
        self.redo_btn = QPushButton("Redo")
        self.save_btn = QPushButton("Save Masks")

        self.draw_btn.clicked.connect(lambda: self.canvas.set_mode('draw'))
        self.erase_btn.clicked.connect(lambda: self.canvas.set_mode('erase'))
        self.undo_btn.clicked.connect(self.canvas.undo)
        self.redo_btn.clicked.connect(self.canvas.redo)
        self.save_btn.clicked.connect(self.save_masks)

        controls_layout = QHBoxLayout()
        controls_layout.addWidget(QLabel("Select Label:"))
        controls_layout.addWidget(self.label_selector)
        controls_layout.addWidget(self.draw_btn)
        controls_layout.addWidget(self.erase_btn)
        controls_layout.addWidget(self.undo_btn)
        controls_layout.addWidget(self.redo_btn)
        controls_layout.addWidget(self.save_btn)

        main_layout = QVBoxLayout(self)
        main_layout.addLayout(controls_layout)
        main_layout.addWidget(self.scroll_area)

        self.resize(1200, 900)

    def change_label(self, label_name):
        self.canvas.set_active_label(label_name)

    def save_masks(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder to Save Masks")
        if not folder:
            return

        import cv2
        for label, mask in self.canvas.labels.items():
            filename = f"{label}_mask.png"
            cv2.imwrite(folder + "/" + filename, mask)

        QMessageBox.information(self, "Save Masks",
                                f"Saved {len(self.canvas.labels)} masks to:\n{folder}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    image_path = "path_to_your_image.jpg"  # Change to your image file
    window = MainWindow(image_path)
    window.show()
    sys.exit(app.exec())
