import os
import numpy as np
import cv2
from PySide6.QtWidgets import QLabel, QMessageBox
from PySide6.QtGui import QPixmap, QImage, QPainter, QColor
from PySide6.QtCore import Qt, QPoint, QSize

from src.utils import FrameMasks

class MaskPainter(QLabel):
    def __init__(self):
        super().__init__()

        # Load the base image in RGB
        self.image = np.zeros((512, 512, 3), dtype=np.uint8)
        self.masks = FrameMasks()

        self.labels = {}
        self.label_colors = {
            "Polyp": QColor(255, 0, 0, 120),
            "Shaft": QColor(0, 255, 0, 120),
            "Wire": QColor(0, 0, 255, 120)
        }

        self.active_label = "Polyp"
        
        self.show_masks = True  # default to visible
        self.mask_view_mode = "All"

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

        self.cursor_pos = QPoint(0, 0)
        self.show_cursor_circle = True
        self.cursor_color_draw = QColor(255, 0, 0, 180)
        self.cursor_color_erase = QColor(0, 0, 255, 180)

        self.update_display()

        # Fix size policy and size to image size initially
        h, w = self.image.shape[:2]
        self.setFixedSize(w, h)

    def set_mask_visibility(self, visible: bool):
        self.show_masks = visible
        self.update_display()

    def set_mask_view_mode(self, mode):
        if mode in ("All", "Current"):
            self.mask_view_mode = mode
            self.update_display()

    def set_image(self, image):
        if image is None or not isinstance(image, np.ndarray):
            raise ValueError("Image must be a valid numpy array.")
        if len(image.shape) != 3 or image.shape[2] != 3:
            raise ValueError("Image must be a 3-channel RGB image.")

        self.image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        # Set the QLabel size to the image size
        h, w = self.image.shape[:2]
        self.setFixedSize(w, h)


    def set_masks(self, masks):
        self.masks = masks

    def reset_zoom(self):
        self._zoom = 1.0

    def sizeHint(self):
        h, w = self.image.shape[:2]
        return QSize(int(w * self._zoom), int(h * self._zoom))

    def set_active_label(self, label_name):
        self.active_label = label_name
        self.update_display()

    def current_mask(self):
        current_mask = self.masks.get(self.active_label)
        if current_mask is None:
            current_mask = np.zeros(self.image.shape[:2], dtype=np.uint8)
        return current_mask

    def set_zoom(self, zoom_factor):
        self.zoom_factor = zoom_factor
        self.update_display()



    def update_display(self):
        h, w = self.image.shape[:2]

        # Create base image QImage
        base_img = QImage(self.image.data, w, h, self.image.strides[0], QImage.Format_RGB888)

        # Create QPixmap to draw on
        pixmap = QPixmap.fromImage(base_img)

        # Create an overlay (RGBA)
        overlay = np.zeros((h, w, 4), dtype=np.uint8)

        if self.show_masks:
            if self.mask_view_mode == "Current":
                mask = self.current_mask()
                if mask is not None:
                    color = self.label_colors[self.active_label]
                    r, g, b, a = color.red(), color.green(), color.blue(), color.alpha()
                    overlay[mask > 0] = [r, g, b, a]
            elif self.mask_view_mode == "All":
                for label, color in self.label_colors.items():
                    mask = self.masks.get(label)
                    if mask is not None:
                        r, g, b, a = color.red(), color.green(), color.blue(), color.alpha()
                        overlay[mask > 0] = [r, g, b, a]

        overlay_img = QImage(overlay.data, w, h, overlay.strides[0], QImage.Format_RGBA8888)
        painter = QPainter(pixmap)
        painter.drawImage(0, 0, overlay_img)
        painter.end()

        # Scale pixmap according to zoom
        scaled_pixmap = pixmap.scaled(int(w * self._zoom), int(h * self._zoom), Qt.KeepAspectRatio)

        # Draw brush/eraser preview circle
        painter = QPainter(scaled_pixmap)
        if self.show_cursor_circle:
            # brush size is thickness (diameter), so radius = size/2
            radius = int((self.pen_size if self.mode == 'draw' else self.eraser_size) * self._zoom / 2)
            if radius < 1:
                radius = 1  # ensure visible minimum radius

            color = self.cursor_color_draw if self.mode == 'draw' else self.cursor_color_erase

            painter.setRenderHint(QPainter.Antialiasing)
            painter.setBrush(color)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(self.cursor_pos, radius, radius)
        painter.end()

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
        self.cursor_pos = event.position().toPoint()
        if self.drawing and self.active_label:
            img_pt = self.widget_to_image(event.position())
            if img_pt is None:
                return

            size = self.pen_size if self.mode == 'draw' else self.eraser_size
            val = 255 if self.mode == 'draw' else 0

            current_mask = cv2.line(
                self.current_mask(),
                (self.last_point.x(), self.last_point.y()),
                (img_pt.x(), img_pt.y()),
                color=val,
                thickness=size
            )

            self.masks.set(mask=current_mask, label=self.active_label)
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


    def undo(self):
        if self.history:
            self.redo_stack.append(self.current_mask().copy())
            last_mask = self.history.pop()
            self.masks.set(mask=last_mask, label=self.active_label)
            self.update_display()

    def redo(self):
        if self.redo_stack:
            self.history.append(self.current_mask().copy())
            next_mask = self.redo_stack.pop()
            self.masks.set(mask=next_mask, label=self.active_label)
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