import sys
import os
from typing import List, Set
from PIL import Image, ImageDraw, ImageFont
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QListWidget, QListWidgetItem, QFileDialog,
    QLabel, QLineEdit, QSlider, QGroupBox, QFormLayout, QMessageBox,
    QComboBox, QRadioButton, QButtonGroup
)
from PySide6.QtGui import QIcon, QPixmap, QPainter, QFont, QColor
from PySide6.QtCore import Qt, QSize, QPointF


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


class PreviewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(320)
        self._pixmap = QPixmap()
        self._wm_text = ""
        self._opacity = 1.0  # 0.0 - 1.0
        # 归一化位置（文本左上角相对图像显示区域的比例坐标）
        self._norm_pos = QPointF(0.8, 0.85)
        self._dragging = False

    def set_image(self, pix: QPixmap):
        self._pixmap = pix if pix and not pix.isNull() else QPixmap()
        self.update()

    def set_text(self, text: str):
        self._wm_text = text or ""
        self.update()

    def set_opacity_percent(self, percent: int):
        self._opacity = max(0.0, min(1.0, percent / 100.0))
        self.update()

    def set_norm_pos(self, x: float, y: float):
        self._norm_pos = QPointF(max(0.0, min(1.0, x)), max(0.0, min(1.0, y)))
        self.update()

    def get_norm_pos(self):
        return float(self._norm_pos.x()), float(self._norm_pos.y())

    def sizeHint(self):
        return QSize(600, 360)

    def _image_draw_rect(self):
        # 计算图像在控件中的显示矩形（等比缩放居中）
        if self._pixmap.isNull():
            return self.rect()
        rw = self.width()
        rh = self.height()
        pw = self._pixmap.width()
        ph = self._pixmap.height()
        if pw == 0 or ph == 0:
            return self.rect()
        scale = min(rw / pw, rh / ph)
        dw = int(pw * scale)
        dh = int(ph * scale)
        x = (rw - dw) // 2
        y = (rh - dh) // 2
        return self.rect().adjusted(x, y, -(rw - dw - x), -(rh - dh - y))

    def _font_for_display(self, disp_w: int):
        size = max(12, disp_w // 20)
        f = QFont()
        f.setPointSizeF(size)
        return f

    def paintEvent(self, _event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(30, 30, 30))
        if self._pixmap.isNull():
            p.setPen(QColor(200, 200, 200))
            p.drawText(self.rect(), Qt.AlignCenter, "请从左侧列表选择一张图片进行预览")
            p.end()
            return

        img_rect = self._image_draw_rect()
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        p.drawPixmap(img_rect, self._pixmap)

        # 计算显示坐标下的位置
        disp_w = img_rect.width()
        disp_h = img_rect.height()
        font = self._font_for_display(disp_w)
        p.setFont(font)
        metrics = p.fontMetrics()
        text_w = metrics.horizontalAdvance(self._wm_text)
        text_h = metrics.height()

        x = int(img_rect.left() + self._norm_pos.x() * disp_w)
        y = int(img_rect.top() + self._norm_pos.y() * disp_h)
        margin = max(6, disp_w // 100)
        x = max(img_rect.left() + margin, min(x, img_rect.right() - text_w - margin))
        y = max(img_rect.top() + margin, min(y, img_rect.bottom() - text_h - margin))

        alpha = int(255 * self._opacity)
        shadow = QColor(0, 0, 0, alpha)
        fore = QColor(255, 255, 255, alpha)
        shadow_offset = max(1, disp_w // 400)
        p.setPen(shadow)
        p.drawText(x + shadow_offset, y + shadow_offset + text_h, self._wm_text)
        p.setPen(fore)
        p.drawText(x, y + text_h, self._wm_text)
        p.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not self._pixmap.isNull():
            self._dragging = True

    def mouseMoveEvent(self, event):
        if not self._dragging or self._pixmap.isNull():
            return
        img_rect = self._image_draw_rect()
        disp_w = img_rect.width()
        disp_h = img_rect.height()
        if disp_w <= 0 or disp_h <= 0:
            return
        rel_x = (event.position().x() - img_rect.left()) / disp_w
        rel_y = (event.position().y() - img_rect.top()) / disp_h
        self.set_norm_pos(rel_x, rel_y)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = False

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

        # Right: preview + settings
        right_box = QVBoxLayout()
        layout.addLayout(right_box, 2)

        # Preview area
        self.preview = PreviewWidget()
        right_box.addWidget(self.preview)

        settings_group = QGroupBox("水印设置")
        right_box.addWidget(settings_group)
        form = QFormLayout()
        settings_group.setLayout(form)

        self.input_text = QLineEdit()
        self.input_text.setPlaceholderText("请输入水印文本内容")
        form.addRow(QLabel("内容："), self.input_text)

        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self.lbl_opacity = QLabel("100%")
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

        # 导出格式
        self.format_combo = QComboBox()
        self.format_combo.addItems(["PNG", "JPEG"])
        form.addRow(QLabel("输出格式："), self.format_combo)

        # 命名规则
        self.rb_keep = QRadioButton("保留原文件名")
        self.rb_prefix = QRadioButton("添加前缀")
        self.rb_suffix = QRadioButton("添加后缀")
        self.rb_keep.setChecked(True)
        self.name_group = QButtonGroup(self)
        self.name_group.addButton(self.rb_keep)
        self.name_group.addButton(self.rb_prefix)
        self.name_group.addButton(self.rb_suffix)
        rule_layout = QHBoxLayout()
        rule_layout.addWidget(self.rb_keep)
        rule_layout.addWidget(self.rb_prefix)
        rule_layout.addWidget(self.rb_suffix)
        form.addRow(QLabel("命名规则："), self.wrap_layout(rule_layout))

        self.input_prefix = QLineEdit()
        self.input_prefix.setPlaceholderText("例如：wm_")
        self.input_prefix.setEnabled(False)
        form.addRow(QLabel("前缀："), self.input_prefix)

        self.input_suffix = QLineEdit()
        self.input_suffix.setPlaceholderText("例如：_watermarked")
        self.input_suffix.setEnabled(False)
        form.addRow(QLabel("后缀："), self.input_suffix)

        # 快速定位（九宫格）
        row1 = QHBoxLayout()
        self.btn_tl = QPushButton("左上")
        self.btn_tc = QPushButton("上中")
        self.btn_tr = QPushButton("右上")
        for b in (self.btn_tl, self.btn_tc, self.btn_tr):
            row1.addWidget(b)
        form.addRow(QLabel("快速定位："), self.wrap_layout(row1))

        row2 = QHBoxLayout()
        self.btn_lc = QPushButton("左中")
        self.btn_center = QPushButton("中心")
        self.btn_rc = QPushButton("右中")
        for b in (self.btn_lc, self.btn_center, self.btn_rc):
            row2.addWidget(b)
        form.addRow(QLabel(""), self.wrap_layout(row2))

        row3 = QHBoxLayout()
        self.btn_bl = QPushButton("左下")
        self.btn_bc = QPushButton("下中")
        self.btn_br = QPushButton("右下")
        for b in (self.btn_bl, self.btn_bc, self.btn_br):
            row3.addWidget(b)
        form.addRow(QLabel(""), self.wrap_layout(row3))

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
        self.rb_keep.toggled.connect(self.on_name_rule_change)
        self.rb_prefix.toggled.connect(self.on_name_rule_change)
        self.rb_suffix.toggled.connect(self.on_name_rule_change)

        # 预览联动
        self.input_text.textChanged.connect(self.on_text_change)
        self.list_widget.currentItemChanged.connect(self.on_list_selection_changed)
        self.list_widget.itemClicked.connect(self.on_list_selection_changed)

        # 快速定位（九宫格）
        self.btn_tl.clicked.connect(lambda: self.set_preview_pos(0.02, 0.02))
        self.btn_tc.clicked.connect(lambda: self.set_preview_pos(0.5, 0.02))
        self.btn_tr.clicked.connect(lambda: self.set_preview_pos(0.98, 0.02))

        self.btn_lc.clicked.connect(lambda: self.set_preview_pos(0.02, 0.5))
        self.btn_center.clicked.connect(lambda: self.set_preview_pos(0.5, 0.5))
        self.btn_rc.clicked.connect(lambda: self.set_preview_pos(0.98, 0.5))

        self.btn_bl.clicked.connect(lambda: self.set_preview_pos(0.02, 0.98))
        self.btn_bc.clicked.connect(lambda: self.set_preview_pos(0.5, 0.98))
        self.btn_br.clicked.connect(lambda: self.set_preview_pos(0.98, 0.98))

    def wrap_layout(self, inner_layout: QHBoxLayout) -> QWidget:
        w = QWidget()
        w.setLayout(inner_layout)
        return w

    def on_opacity_change(self, val: int):
        self.lbl_opacity.setText(f"{val}%")
        # 预览透明度实时更新
        self.preview.set_opacity_percent(val)

    def on_name_rule_change(self, checked: bool):
        # 启用/禁用前缀/后缀输入框
        use_prefix = self.rb_prefix.isChecked()
        use_suffix = self.rb_suffix.isChecked()
        self.input_prefix.setEnabled(use_prefix)
        self.input_suffix.setEnabled(use_suffix)

    def on_text_change(self, t: str):
        self.preview.set_text(t or "")

    def on_list_selection_changed(self, *_):
        item = self.list_widget.currentItem()
        if not item:
            return
        p = item.data(Qt.UserRole)
        pix = QPixmap(p)
        self.preview.set_image(pix)

    def set_preview_pos(self, nx: float, ny: float):
        self.preview.set_norm_pos(nx, ny)

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
        fmt = (self.format_combo.currentText() or "PNG").upper()
        name_rule = "keep"
        if self.rb_prefix.isChecked():
            name_rule = "prefix"
        elif self.rb_suffix.isChecked():
            name_rule = "suffix"
        prefix_text = self.input_prefix.text().strip()
        suffix_text = self.input_suffix.text().strip()

        if not export_dir:
            QMessageBox.warning(self, "提示", "请先选择导出目录。")
            return
        if not os.path.isdir(export_dir):
            try:
                os.makedirs(export_dir, exist_ok=True)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法创建导出目录：{e}")
                return

        # 改为总是导出列表中的所有图片（与选中状态无关）
        paths = [self.list_widget.item(i).data(Qt.UserRole) for i in range(self.list_widget.count())]
        if not paths:
            QMessageBox.information(self, "提示", "请先导入图片。")
            return

        # 禁止导出到原文件夹（默认不允许）
        exp_norm = os.path.normcase(os.path.abspath(export_dir))
        for p in paths:
            src_dir = os.path.normcase(os.path.abspath(os.path.dirname(p)))
            if exp_norm == src_dir:
                QMessageBox.warning(self, "禁止导出到源目录", "为防止覆盖原图，禁止将导出路径设置为源图片所在文件夹。请更换导出目录。")
                return
        if not wm_text:
            res = QMessageBox.question(self, "确认", "水印内容为空，是否继续？", QMessageBox.Yes | QMessageBox.No)
            if res != QMessageBox.Yes:
                return

        self.btn_process.setEnabled(False)
        self.btn_add_files.setEnabled(False)
        self.btn_add_dir.setEnabled(False)
        self.btn_clear.setEnabled(False)

        # 从预览获取归一化位置
        norm_x, norm_y = self.preview.get_norm_pos()

        failed = []
        for p in paths:
            try:
                self.apply_watermark(p, wm_text, opacity_percent, export_dir, fmt, name_rule, prefix_text, suffix_text, norm_x, norm_y)
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

    def apply_watermark(self, img_path: str, text: str, opacity_percent: int, export_dir: str, fmt: str, name_rule: str, prefix_text: str, suffix_text: str, norm_x: float, norm_y: float):
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
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        # 使用预览的归一化坐标定位（文本左上角）
        W, H = base.size
        margin = max(10, W // 100)
        x = int(norm_x * W)
        y = int(norm_y * H)
        x = max(margin, min(x, W - text_w - margin))
        y = max(margin, min(y, H - text_h - margin))

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

        # 输出文件名与格式
        base_name, _ = os.path.splitext(os.path.basename(img_path))
        if name_rule == "prefix" and prefix_text:
            out_base = f"{prefix_text}{base_name}"
        elif name_rule == "suffix" and suffix_text:
            out_base = f"{base_name}{suffix_text}"
        else:
            out_base = base_name

        out_ext = ".png" if fmt == "PNG" else ".jpg"
        out_path = os.path.join(export_dir, out_base + out_ext)

        # 保存为指定格式
        if fmt == "JPEG":
            to_save = combined.convert("RGB")  # JPEG 不支持透明
            to_save.save(out_path, "JPEG", quality=90, subsampling=0, optimize=True)
        else:
            to_save = combined.convert("RGBA")
            to_save.save(out_path, "PNG", optimize=True)

        # Close resources
        img.close()
        save_img.close()


def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    # 初始预览联动
    w.preview.set_opacity_percent(w.opacity_slider.value())
    w.input_text.textChanged.connect(lambda t: w.preview.set_text(t or ""))
    if w.list_widget.count() > 0:
        first = w.list_widget.item(0)
        if first:
            w.list_widget.setCurrentItem(first)
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()