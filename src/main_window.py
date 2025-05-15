import os
import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QFileDialog, QMessageBox,
    QLabel, QScrollArea, QSlider
)
from PySide6.QtCore import Qt

from src.components import MaskPainter
from src.utils import DataLoader


class MainWindow(QWidget):
    def __init__(self, image_path):
        super().__init__()

        self.setWindowTitle("Semantic Segmentation Annotation")

        self.data_loader = None
        self.load_video_btn = QPushButton("Load Video")
        self.load_video_btn.clicked.connect(self.load_video)

        self.frame_slider = QSlider(Qt.Horizontal)
        self.frame_slider.setRange(0, 1)
        self.frame_slider.setValue(0)
        self.frame_slider.setTracking(True)
        self.frame_slider.setSingleStep(1)
        self.frame_slider.setPageStep(1)
        self.frame_slider.valueChanged.connect(self.load_frame)

        self.canvas = MaskPainter()
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.canvas)

        self.label_selector = QComboBox()
        default_labels = ["Polyp", "Wire", "Shaft"]
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
        main_layout.addWidget(self.load_video_btn)
        main_layout.addWidget(self.frame_slider)
        main_layout.addWidget(self.scroll_area)
        main_layout.addLayout(controls_layout)

        self.resize(1200, 900)

    def load_video(self):
        video_dir = QFileDialog.getExistingDirectory(self, "Select Video Directory")
        if not video_dir:
            return
        
        self.video = video_dir
        self.data_loader = DataLoader(video_dir, ["Wire", "Shaft", "Polyp"])
        self.frame_slider.setRange(0, self.data_loader.frame_count - 1)
        self.current_frame_number = 0

        self.canvas.update_display()

    def load_frame(self, frame_number):
        if self.data_loader is None:
            return

        self.data_loader.set_frame_masks(self.current_frame_number, self.canvas.masks)

        self.current_frame_number = frame_number

        self.current_frame = self.data_loader.get_frame(frame_number)
        self.canvas.set_image(self.current_frame)

        current_masks = self.data_loader.get_masks(frame_number)
        self.canvas.set_masks(current_masks)

        # Reset the zoom in the canvas
        self.canvas.reset_zoom()

        self.canvas.update_display()

    def change_label(self, label_name):
        self.canvas.set_active_label(label_name)

    def save_masks(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder to Save Masks")
        if not folder:
            return

        folder = folder + "/" + self.data_loader.video_path.stem
        if not os.path.exists(folder):
            os.makedirs(folder)

        self.data_loader.save_all_masks(folder)

        QMessageBox.information(self, "Save Masks",
                                f"Saved masks to:\n{folder}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    image_path = "path_to_your_image.jpg"  # Change to your image file
    window = MainWindow(image_path)
    window.show()
    sys.exit(app.exec())
