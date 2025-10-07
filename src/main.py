import sys
import os
from typing import List, Set
from PIL import Image, ImageDraw, ImageFont
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QListWidget, QListWidgetItem, QFileDialog,
    QLabel, QLineEdit, QSlider, QGroupBox, QFormLayout, QMessageBox
)
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import Qt, QSize


SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".webp"}


def is_image_file(path: str) -> bool:
    ext = os.path.splitext(path)[1].lower()
    return ext in SUPPORTED_EXTS


def collect_images_from_folder(folder: str) -> List[str]:
    result = []
    for root, _, files in os.walk(folder):
        for f in files:
            p = os.path.join(root, f)
            if is_image_file(p):
                result.append(p)
    return result


class ImageListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QListWidget.MultiSelection)
        self.setIconSize(QSize(96, 96))
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.DropOnly)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            paths = []
            for url in event.mimeData().urls():
                local = url.toLocalFile()
                if os.path.isdir(local):
                    paths.extend(collect_images_from_folder(local))
                elif os.path.isfile(local) and is_image_file(local):
                    paths.append(local)
            self.add_image_items(paths)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

    def add_image_items(self, paths: List[str]):
        existing: Set[str] = set()
        for i in range(self.count()):
            item = self.item(i)
            existing.add(item.data(Qt.UserRole))

        for p in paths:
            if not p or p in existing:
                continue
            item = QListWidgetItem()
            item.setText(os.path.basename(p))
            item.setToolTip(p)
            item.setData(Qt.UserRole, p)
            # thumbnail
            pixmap = QPixmap(p)
            if not pixmap.isNull():
                thumb = pixmap.scaled(self.iconSize(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                item.setIcon(QIcon(thumb))
            self.addItem(item)

    def get_selected_paths(self) -> List[str]:
        selected = self.selectedItems()
        if not selected:
            # if none selected, default to all
            return [self.item(i).data(Qt.UserRole) for i in range(self.count())]
        return [it.data(Qt.UserRole) for it in selected]

    def clear_all(self):
        self.clear()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("图片批量水印工具")
        self.setMinimumSize(900, 600)

        root = QWidget()
        self.setCentralWidget(root)

        layout = QHBoxLayout()
        root.setLayout(layout)

        # Left: list and controls
        left_box = QVBoxLayout()
        layout.addLayout(left_box, 2)

        self.list_widget = ImageListWidget()
        left_box.addWidget(self.list_widget)

        btn_bar = QHBoxLayout()
        left_box.addLayout(btn_bar)

        self.btn_add_files = QPushButton("添加图片")
        self.btn_add_dir = QPushButton("添加文件夹")
        self.btn_clear = QPushButton("清空列表")
        btn_bar.addWidget(self.btn_add_files)
        btn_bar.addWidget(self.btn_add_dir)
        btn_bar.addStretch()
        btn_bar.addWidget(self.btn_clear)

        # Right: settings
        right_box = QVBoxLayout()
        layout.addLayout(right_box, 1)

        settings_group = QGroupBox("水印设置")
        right_box.addWidget(settings_group)
        form = QFormLayout()
        settings_group.setLayout(form)

        self.input_text = QLineEdit()
        self.input_text.setPlaceholderText("请输入水印文本内容")
        form.addRow(QLabel("内容："), self.input_text)

        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(30)
        self.lbl_opacity = QLabel("30%")
        op_layout = QHBoxLayout()
        op_layout.addWidget(self.opacity_slider)
        op_layout.addWidget(self.lbl_opacity)
        form.addRow(QLabel("透明度："), self.wrap_layout(op_layout))

        self.export_path = QLineEdit()
        self.export_path.setPlaceholderText("请选择导出目录")
        self.btn_choose_export = QPushButton("选择路径")
        exp_layout = QHBoxLayout()
        exp_layout.addWidget(self.export_path)
        exp_layout.addWidget(self.btn_choose_export)
        form.addRow(QLabel("导出路径："), self.wrap_layout(exp_layout))

        right_box.addStretch()

        self.btn_process = QPushButton("开始处理")
        right_box.addWidget(self.btn_process)

        # Connections
        self.btn_add_files.clicked.connect(self.add_files)
        self.btn_add_dir.clicked.connect(self.add_folder)
        self.btn_clear.clicked.connect(self.list_widget.clear_all)
        self.btn_choose_export.clicked.connect(self.choose_export_dir)
        self.btn_process.clicked.connect(self.process_images)
        self.opacity_slider.valueChanged.connect(self.on_opacity_change)

    def wrap_layout(self, inner_layout: QHBoxLayout) -> QWidget:
        w = QWidget()
        w.setLayout(inner_layout)
        return w

    def on_opacity_change(self, val: int):
        self.lbl_opacity.setText(f"{val}%")

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择图片", "", "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp);;所有文件 (*.*)"
        )
        files = [f for f in files if is_image_file(f)]
        self.list_widget.add_image_items(files)

    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹", "")
        if folder:
            imgs = collect_images_from_folder(folder)
            self.list_widget.add_image_items(imgs)

    def choose_export_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "选择导出目录", "")
        if folder:
            self.export_path.setText(folder)

    def process_images(self):
        export_dir = self.export_path.text().strip()
        wm_text = self.input_text.text().strip()
        opacity_percent = self.opacity_slider.value()

        if not export_dir:
            QMessageBox.warning(self, "提示", "请先选择导出目录。")
            return
        if not os.path.isdir(export_dir):
            try:
                os.makedirs(export_dir, exist_ok=True)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法创建导出目录：{e}")
                return

        paths = self.list_widget.get_selected_paths()
        if not paths:
            QMessageBox.information(self, "提示", "请先导入图片。")
            return
        if not wm_text:
            res = QMessageBox.question(self, "确认", "水印内容为空，是否继续？", QMessageBox.Yes | QMessageBox.No)
            if res != QMessageBox.Yes:
                return

        self.btn_process.setEnabled(False)
        self.btn_add_files.setEnabled(False)
        self.btn_add_dir.setEnabled(False)
        self.btn_clear.setEnabled(False)

        failed = []
        for p in paths:
            try:
                self.apply_watermark(p, wm_text, opacity_percent, export_dir)
            except Exception as e:
                failed.append((p, str(e)))

        self.btn_process.setEnabled(True)
        self.btn_add_files.setEnabled(True)
        self.btn_add_dir.setEnabled(True)
        self.btn_clear.setEnabled(True)

        if failed:
            msg = "\n".join([f"{os.path.basename(p)}: {err}" for p, err in failed])
            QMessageBox.warning(self, "部分失败", f"以下文件处理失败：\n{msg}")
        else:
            QMessageBox.information(self, "完成", "全部图片处理完成！")

    def apply_watermark(self, img_path: str, text: str, opacity_percent: int, export_dir: str):
        # Open image
        img = Image.open(img_path)
        img_mode = img.mode
        base = img.convert("RGBA")

        # Create transparent layer for watermark
        watermark = Image.new("RGBA", base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(watermark)

        # Choose font
        font = None
        # Try common Windows fonts; fallback to default
        candidates = [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/msyh.ttc",  # 微软雅黑
            "C:/Windows/Fonts/simhei.ttf",  # 黑体
            "C:/Windows/Fonts/simsun.ttc",  # 宋体
        ]
        for fp in candidates:
            if os.path.exists(fp):
                try:
                    # font size relative to image width
                    font = ImageFont.truetype(fp, max(16, base.size[0] // 20))
                    break
                except Exception:
                    continue
        if font is None:
            font = ImageFont.load_default()

        # Compute text size
        # Use getbbox for modern PIL versions
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        # Position bottom-right with margin
        margin = max(10, base.size[0] // 100)
        x = base.size[0] - text_w - margin
        y = base.size[1] - text_h - margin
        x = max(margin, x)
        y = max(margin, y)

        # Opacity to alpha channel
        alpha = int(255 * (opacity_percent / 100.0))

        # Draw shadow for readability
        shadow_offset = max(1, base.size[0] // 400)
        if text:
            draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=(0, 0, 0, alpha))
            draw.text((x, y), text, font=font, fill=(255, 255, 255, alpha))

        # Composite
        combined = Image.alpha_composite(base, watermark)

        # Convert back to original mode for saving
        save_img = combined.convert(img_mode if img_mode != "P" else "RGBA")

        # Save with same filename to export_dir
        fname = os.path.basename(img_path)
        out_path = os.path.join(export_dir, fname)

        # Ensure extension compatible; use original format if possible
        try:
            save_img.save(out_path)
        except Exception:
            # Fallback to PNG
            base_name, _ = os.path.splitext(out_path)
            out_path = base_name + ".png"
            save_img.save(out_path)

        # Close resources
        img.close()
        save_img.close()


def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()