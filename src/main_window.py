import os
import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QFileDialog, QMessageBox,
    QLabel, QScrollArea, QSlider
)
from PySide6.QtCore import Qt

from src.components import MaskPainter
from src.utils import VideoDataLoader, ImageDataLoader

from PySide6.QtGui import QKeySequence, QShortcut

class MainWindow(QWidget):
    def __init__(self, config):
        super().__init__()

        self.setWindowTitle("Semantic Segmentation Annotation")

        self.config = config
        app_type = config.get("application", "Image")

        if app_type == "Image":
            self.load_button, self.slider = self.init_image_mode()
        elif app_type == "Video":
            self.load_button, self.slider = self.init_video_mode()


        self.data_loader = None

        # Shortcut to go to previous frame
        self.shortcut_prev_frame = QShortcut(QKeySequence("N"), self)
        self.shortcut_prev_frame.activated.connect(self.decrease_frame)

        # Shortcut to go to next frame
        self.shortcut_next_frame = QShortcut(QKeySequence("M"), self)
        self.shortcut_next_frame.activated.connect(self.increase_frame)

        self.labels = config.get("labels", ["Label1", "Label2", "Label3"])


        self.canvas = MaskPainter(labels=self.labels)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.canvas)

        self.label_selector = QComboBox()
        default_labels = config.get("labels", ["Label1", "Label2", "Label3"])
        self.label_selector.addItems(default_labels)
        self.label_selector.currentTextChanged.connect(self.change_label)
        self.canvas.set_active_label(default_labels[0])

        self.shortcut_cycle_label = QShortcut(QKeySequence("X"), self)
        self.shortcut_cycle_label.activated.connect(self.cycle_label_selector)

                # === View Mode Selector ===
        self.view_selector = QComboBox()
        self.view_selector.addItems(["All Masks", "Current Mask"])
        self.view_selector.currentTextChanged.connect(self.change_view_mode)

        # === Mask Visibility Toggle ===
        self.show_mask_selector = QComboBox()
        self.show_mask_selector.addItems(["Yes", "No"])
        self.show_mask_selector.currentTextChanged.connect(self.toggle_mask_visibility)

        self.view_layout = QHBoxLayout()
        self.view_layout.addWidget(QLabel("View:"))
        self.view_layout.addWidget(self.view_selector)
        self.view_layout.addWidget(QLabel("Show Mask:"))
        self.view_layout.addWidget(self.show_mask_selector)

        # === Shortcuts ===
        self.toggle_view_shortcut = QShortcut(QKeySequence("C"), self)
        self.toggle_view_shortcut.activated.connect(self.cycle_view_selector)

        self.toggle_visibility_shortcut = QShortcut(QKeySequence("V"), self)
        self.toggle_visibility_shortcut.activated.connect(self.cycle_visibility_selector)

        # Default settings
        self.canvas.set_mask_visibility(True)
        self.canvas.set_mask_view_mode("All")

        self.draw_btn = QPushButton("Draw")
        self.erase_btn = QPushButton("Erase")
        self.undo_btn = QPushButton("Undo")
        self.redo_btn = QPushButton("Redo")
        self.delete_btn = QPushButton("Delete Mask")
        self.save_btn = QPushButton("Save Masks")

        self.draw_btn.clicked.connect(lambda: self.canvas.set_mode('draw'))
        self.erase_btn.clicked.connect(lambda: self.canvas.set_mode('erase'))
        self.undo_btn.clicked.connect(self.canvas.undo)
        self.redo_btn.clicked.connect(self.canvas.redo)
        self.delete_btn.clicked.connect(self.delete_current_mask)
        self.save_btn.clicked.connect(self.save_masks)

        # Set a shortcut for the draw button
        self.draw_btn.setShortcut("B")
        self.erase_btn.setShortcut("E")
        self.undo_btn.setShortcut("Ctrl+Z")
        self.redo_btn.setShortcut("Ctrl+Y")
        self.delete_btn.setShortcut("Ctrl+D")

        self.brush_slider = QSlider(Qt.Horizontal)
        self.brush_slider.setRange(1, 50)
        self.brush_slider.setValue(5)  # default size
        self.brush_slider.valueChanged.connect(self.change_brush_size)


        # Make brush size increase with Q and decrease with Shift+Q
        self.shortcut_increase_brush = QShortcut(QKeySequence("Q"), self)
        self.shortcut_increase_brush.activated.connect(lambda: self.brush_slider.setValue(self.brush_slider.value() + 1))

        self.shortcut_decrease_brush = QShortcut(QKeySequence("Shift+Q"), self)
        self.shortcut_decrease_brush.activated.connect(lambda: self.brush_slider.setValue(self.brush_slider.value() - 1))

        controls_layout = QHBoxLayout()
        controls_layout.addWidget(QLabel("Select Label:"))
        controls_layout.addWidget(self.label_selector)
        controls_layout.addLayout(self.view_layout)
        controls_layout.addWidget(QLabel("Brush Size:"))
        controls_layout.addWidget(self.brush_slider)
        controls_layout.addWidget(self.draw_btn)
        controls_layout.addWidget(self.erase_btn)
        controls_layout.addWidget(self.undo_btn)
        controls_layout.addWidget(self.redo_btn)
        controls_layout.addWidget(self.delete_btn)
        controls_layout.addWidget(self.save_btn)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.load_button)
        main_layout.addWidget(self.slider)
        main_layout.addWidget(self.scroll_area)
        main_layout.addLayout(controls_layout)

        self.resize(1200, 900)



##########################################
    def init_video_mode(self):
        load_video_btn = QPushButton("Load Video")
        load_video_btn.clicked.connect(self.load_video)

        frame_slider = QSlider(Qt.Horizontal)
        frame_slider.setRange(0, 1)
        frame_slider.setValue(0)
        frame_slider.setTracking(True)
        frame_slider.setSingleStep(1)
        frame_slider.setPageStep(1)
        frame_slider.valueChanged.connect(self.load_image)

        return load_video_btn, frame_slider


    def init_image_mode(self):
        load_csv_btn = QPushButton("Load CSV")
        load_csv_btn.clicked.connect(self.load_csv)

        slider = QSlider(Qt.Horizontal)
        slider.setRange(0, 1)
        slider.setValue(0)
        slider.setTracking(True)
        slider.setSingleStep(1)
        slider.setPageStep(1)
        slider.valueChanged.connect(self.load_image)

        return load_csv_btn, slider
    
    def load_csv(self):
        csv_file, _ = QFileDialog.getOpenFileName(self, "Open CSV File", "", "CSV Files (*.csv)")
        if not csv_file:
            return
        self.data_loader = ImageDataLoader(csv_file, self.labels)
        self.slider.setRange(0, self.data_loader.max_index - 1)
        self.current_index = 0

    def load_image(self, index):
        # Placeholder for loading image logic
        pass

##########################################
    def delete_current_mask(self):
        current_frame = self.slider.value()
        if current_frame in self.data_loader.masks:
            self.data_loader.delete_mask(current_frame, self.canvas.active_label)
            self.canvas.set_masks(self.data_loader.get_masks(current_frame))
            self.canvas.update_display()
        else:
            QMessageBox.warning(self, "Warning", "No mask to delete for the current frame.")
##########################################


    def cycle_label_selector(self):
        current_index = self.label_selector.currentIndex()
        total_items = self.label_selector.count()
        new_index = (current_index + 1) % total_items
        self.label_selector.setCurrentIndex(new_index)

    def decrease_frame(self):
        current_value = self.slider.value()
        if current_value > self.slider.minimum():
            self.slider.setValue(current_value - 1)

    def increase_frame(self):
        current_value = self.slider.value()
        if current_value < self.slider.maximum():
            self.slider.setValue(current_value + 1)

    def change_view_mode(self, mode_text):
        if mode_text == "All Masks":
            self.canvas.set_mask_view_mode("All")
        elif mode_text == "Current Mask":
            self.canvas.set_mask_view_mode("Current")

    def toggle_mask_visibility(self, show_text):
        self.canvas.set_mask_visibility(show_text == "Yes")

    def cycle_view_selector(self):
        current_index = self.view_selector.currentIndex()
        next_index = (current_index + 1) % self.view_selector.count()
        self.view_selector.setCurrentIndex(next_index)

    def cycle_visibility_selector(self):
        current_index = self.show_mask_selector.currentIndex()
        next_index = (current_index + 1) % self.show_mask_selector.count()
        self.show_mask_selector.setCurrentIndex(next_index)

    def change_brush_size(self, value):
        self.canvas.set_pen_size(value)
        self.canvas.set_eraser_size(value)

    def load_video(self):
        video_dir = QFileDialog.getExistingDirectory(self, "Select Video Directory")
        if not video_dir:
            return
        
        self.video = video_dir
        self.data_loader = VideoDataLoader(video_dir, self.labels)
        self.slider.setRange(0, self.data_loader.max_index - 1)
        self.current_index = 0

        self.canvas.update_display()

    def load_image(self, image_index):
        if self.data_loader is None:
            return

        self.data_loader.set_frame_masks(self.current_index, self.canvas.masks)

        self.current_index = image_index

        self.current_frame = self.data_loader.get_datapoint(image_index)
        self.canvas.set_image(self.current_frame)

        current_masks = self.data_loader.get_masks(image_index)
        self.canvas.set_masks(current_masks)

        # Reset the zoom in the canvas
        self.canvas.reset_zoom()

        self.canvas.update_display()

    def change_label(self, label_name):
        self.canvas.set_active_label(label_name)

    def change_mask_view(self, mode):
        self.canvas.set_mask_view_mode(mode)

    def save_masks(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder to Save Masks")
        if not folder:
            return

        


        folder = folder + "/" + self.data_loader.get_output_dir_name()
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
