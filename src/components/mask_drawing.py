import os
import numpy as np
import cv2
from PySide6.QtWidgets import QLabel, QMessageBox
from PySide6.QtGui import QPixmap, QImage, QPainter, QColor
from PySide6.QtCore import Qt, QPoint, QSize


class MaskPainter(QLabel):
    def __init__(self, image_path):
        super().__init__()

        # Load the base image in RGB
        self.image = cv2.cvtColor(cv2.imread(image_path), cv2.COLOR_BGR2RGB)
        if self.image is None:
            raise FileNotFoundError(f"Image not found: {image_path}")

        self.labels = {}
        self.label_colors = {}
        self.active_label = None

        self.pen_size = 5
        self.eraser_size = 20
        self.mode = 'draw'

        self.drawing = False
        self.last_point = None

        self.history = []
        self.redo_stack = []

        self._zoom = 1.0
        self._zoom_min = 0.2
        self._zoom_max = 5.0

        self.setMouseTracking(True)

        self.update_display()

        # Fix size policy and size to image size initially
        h, w = self.image.shape[:2]
        self.setFixedSize(w, h)

    def sizeHint(self):
        h, w = self.image.shape[:2]
        return QSize(int(w * self._zoom), int(h * self._zoom))

    def set_active_label(self, label_name):
        self.active_label = label_name
        if label_name not in self.labels:
            h, w = self.image.shape[:2]
            self.labels[label_name] = np.zeros((h, w), dtype=np.uint8)
            hue = (len(self.labels) * 45) % 360
            self.label_colors[label_name] = QColor.fromHsv(hue, 255, 255, 120)
        self.update_display()

    def current_mask(self):
        return self.labels[self.active_label]

    def update_display(self):
        h, w = self.image.shape[:2]

        # Create base image QImage
        base_img = QImage(self.image.data, w, h, self.image.strides[0], QImage.Format_RGB888)

        # Create QPixmap to draw on
        pixmap = QPixmap.fromImage(base_img)

        # Overlay mask if active_label exists
        if self.active_label:
            mask = self.current_mask()
            color = self.label_colors[self.active_label]
            r, g, b, a = color.red(), color.green(), color.blue(), color.alpha()

            # Create overlay image (RGBA)
            overlay = np.zeros((h, w, 4), dtype=np.uint8)
            overlay[mask > 0] = [r, g, b, a]

            overlay_img = QImage(overlay.data, w, h, overlay.strides[0], QImage.Format_RGBA8888)
            painter = QPainter(pixmap)
            painter.drawImage(0, 0, overlay_img)
            painter.end()

        # Scale pixmap according to zoom
        scaled_pixmap = pixmap.scaled(int(w * self._zoom), int(h * self._zoom), Qt.KeepAspectRatio)

        self.setPixmap(scaled_pixmap)
        # IMPORTANT: keep QLabel fixed size to scaled pixmap size
        self.setFixedSize(scaled_pixmap.size())
    def widget_to_image(self, pos):
        """Convert widget coordinates to image pixel coordinates."""
        x = int(pos.x() / self._zoom)
        y = int(pos.y() / self._zoom)
        h, w = self.image.shape[:2]
        if 0 <= x < w and 0 <= y < h:
            return QPoint(x, y)
        return None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.active_label:
            img_pt = self.widget_to_image(event.position())
            if img_pt is None:
                return
            self.drawing = True
            self.last_point = img_pt

            # Save undo state
            self.history.append(self.current_mask().copy())
            if len(self.history) > 50:
                self.history.pop(0)
            self.redo_stack.clear()

    def mouseMoveEvent(self, event):
        if self.drawing and self.active_label:
            img_pt = self.widget_to_image(event.position())
            if img_pt is None:
                return

            size = self.pen_size if self.mode == 'draw' else self.eraser_size
            val = 255 if self.mode == 'draw' else 0

            cv2.line(self.current_mask(),
                     (self.last_point.x(), self.last_point.y()),
                     (img_pt.x(), img_pt.y()),
                     color=val,
                     thickness=size)

            self.last_point = img_pt
            self.update_display()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drawing = False

    def wheelEvent(self, event):
        angle_delta = event.angleDelta().y()
        factor = 1.1 if angle_delta > 0 else 0.9
        old_zoom = self._zoom
        new_zoom = self._zoom * factor
        new_zoom = max(self._zoom_min, min(self._zoom_max, new_zoom))

        # Zoom relative to cursor position
        cursor_pos = event.position()
        scroll_area = self.parent()
        if hasattr(scroll_area, 'horizontalScrollBar') and hasattr(scroll_area, 'verticalScrollBar'):
            h_scroll = scroll_area.horizontalScrollBar()
            v_scroll = scroll_area.verticalScrollBar()

            rel_x = (cursor_pos.x() + h_scroll.value()) / old_zoom
            rel_y = (cursor_pos.y() + v_scroll.value()) / old_zoom

            self._zoom = new_zoom
            self.update_display()

            new_rel_x = rel_x * new_zoom
            new_rel_y = rel_y * new_zoom

            h_scroll.setValue(int(new_rel_x - cursor_pos.x()))
            v_scroll.setValue(int(new_rel_y - cursor_pos.y()))
        else:
            self._zoom = new_zoom
            self.update_display()

    def widget_to_image(self, pos):
        # Convert widget coords to image coords
        x = int(pos.x() / self._zoom)
        y = int(pos.y() / self._zoom)
        h, w = self.image.shape[:2]
        if 0 <= x < w and 0 <= y < h:
            return QPoint(x, y)
        return None

    def undo(self):
        if self.history:
            self.redo_stack.append(self.current_mask().copy())
            last_mask = self.history.pop()
            self.labels[self.active_label] = last_mask
            self.update_display()

    def redo(self):
        if self.redo_stack:
            self.history.append(self.current_mask().copy())
            next_mask = self.redo_stack.pop()
            self.labels[self.active_label] = next_mask
            self.update_display()

    def set_mode(self, mode):
        if mode in ('draw', 'erase'):
            self.mode = mode

    def set_pen_size(self, size):
        self.pen_size = size

    def set_eraser_size(self, size):
        self.eraser_size = size

    def load_mask_for_label(self, label_name: str, mask_path: str):
        if not os.path.exists(mask_path):
            QMessageBox.warning(self, "Load Mask", f"Mask file does not exist:\n{mask_path}")
            return

        mask_img = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
        if mask_img is None:
            QMessageBox.warning(self, "Load Mask", f"Failed to load mask:\n{mask_path}")
            return

        h, w = self.image.shape[:2]
        if mask_img.shape != (h, w):
            mask_img = cv2.resize(mask_img, (w, h), interpolation=cv2.INTER_NEAREST)

        _, binary_mask = cv2.threshold(mask_img, 127, 255, cv2.THRESH_BINARY)

        self.labels[label_name] = binary_mask
        if label_name not in self.label_colors:
            hue = (len(self.labels) * 45) % 360
            self.label_colors[label_name] = QColor.fromHsv(hue, 255, 255, 120)

        if self.active_label == label_name:
            self.update_display()