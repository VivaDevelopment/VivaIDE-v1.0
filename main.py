import sys
from PyQt5.QtCore import Qt, QRect, QRectF, QSize, QTimer
from PyQt5.QtGui import QColor, QPainter, QFont, QTextFormat, QTextCursor, QPainterPath, QRegion, QPixmap
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPlainTextEdit, QTextEdit,
    QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QSizePolicy,
    QMenuBar, QFileDialog, QAction, QDialog, QSplashScreen
)
import sys
import os
from PyQt5.QtGui import QIcon, QPixmap

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and PyInstaller """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.code_editor = editor

    def sizeHint(self):
        return QSize(int(self.code_editor.line_number_area_width() * 1.0), 0)  # Slightly wider now

    def paintEvent(self, event):
        self.code_editor.lineNumberAreaPaintEvent(event)

class CodeEditor(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.setFont(QFont("Consolas", 14))
        self.line_number_area = LineNumberArea(self)

        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.highlightCurrentLine)

        self.updateLineNumberAreaWidth(0)
        self.highlightCurrentLine()

        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1e2a47;
                color: #d4d4d4;
                border: none;
                padding-left: 0px;
                selection-background-color: #264f78;
                font-family: Consolas, Courier New, monospace;
                font-size: 14pt;
            }
        """)

    def line_number_area_width(self):
        digits = len(str(max(1, self.blockCount())))
        space = 10 + self.fontMetrics().width('9') * digits
        return int(space * 1.0)  # Slightly wider now

    def updateLineNumberAreaWidth(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def updateLineNumberArea(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#18181f"))

        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        painter.setFont(self.font())
        fm = self.fontMetrics()

        painter.setPen(QColor("#858585"))

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
                painter.drawText(0, int(top), self.line_number_area.width() - 5, fm.height(),
                                 Qt.AlignRight, number)
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            blockNumber += 1

    def highlightCurrentLine(self):
        extraSelections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(QColor("#2a2a3d"))
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extraSelections.append(selection)
        self.setExtraSelections(extraSelections)

class CustomTitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setFixedHeight(28)
        self.setStyleSheet("background-color: #18181f;")

        self.buttons = QWidget()
        self.buttons_layout = QHBoxLayout()
        self.buttons_layout.setContentsMargins(12, 0, 0, 0)
        self.buttons_layout.setSpacing(8)
        self.buttons.setLayout(self.buttons_layout)

        self.close_btn = QPushButton()
        self.close_btn.setFixedSize(13, 13)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff5f56;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background-color: #ff1e1e;
            }
        """)
        self.close_btn.clicked.connect(self.parent.close)

        self.minimize_btn = QPushButton()
        self.minimize_btn.setFixedSize(13, 13)
        self.minimize_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffbd2e;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background-color: #ffb300;
            }
        """)
        self.minimize_btn.clicked.connect(self.parent.showMinimized)

        self.maximize_btn = QPushButton()
        self.maximize_btn.setFixedSize(13, 13)
        self.maximize_btn.setStyleSheet("""
            QPushButton {
                background-color: #27c93f;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background-color: #12a230;
            }
        """)
        self.maximize_btn.clicked.connect(self.toggle_maximize_restore)

        self.buttons_layout.addWidget(self.close_btn)
        self.buttons_layout.addWidget(self.minimize_btn)
        self.buttons_layout.addWidget(self.maximize_btn)

        self.title = QLabel("VivaIDE")
        self.title.setStyleSheet("color: #ddd; font-weight: bold; font-size: 14pt;")
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 15, 0)
        layout.addWidget(self.buttons, alignment=Qt.AlignLeft)
        layout.addStretch()
        layout.addWidget(self.title)
        layout.addStretch()

        self._drag_pos = None

    def toggle_maximize_restore(self):
        if self.parent.isMaximized():
            self.parent.showNormal()
        else:
            self.parent.showMaximized()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.parent.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == Qt.LeftButton:
            self.parent.move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        event.accept()

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)
        self.resize(400, 250)

        self.bg = QWidget(self)
        self.bg.setStyleSheet("""
            background-color: white;
            border-radius: 10px;
            border: 1px solid #ccc;
        """)
        self.bg.setGeometry(0, 0, 400, 250)

        self.close_btn = QPushButton(self.bg)
        self.close_btn.setFixedSize(16, 16)
        self.close_btn.move(370, 10)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff5f56;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover {
                background-color: #ff1e1e;
            }
        """)
        self.close_btn.clicked.connect(self.close)

        self.label = QLabel(self.bg)
        self.label.setGeometry(20, 40, 360, 180)
        self.label.setText(
            "VivaIDE\n\n"
            "Programmer: VivaProjects\n"
            "[Version: 1.00.0]\n\n"
            "Customer Support: vivaprojectsoffical@gmail.com"
        )
        self.label.setStyleSheet("color: black; font-family: Consolas, monospace; font-size: 12pt;")
        self.label.setWordWrap(True)

        self._drag_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        event.accept()

    def showEvent(self, event):
        if self.parent():
            parent_rect = self.parent().geometry()
            self.move(
                parent_rect.center().x() - self.width() // 2,
                parent_rect.center().y() - self.height() // 2,
            )
        super().showEvent(event)

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowSystemMenuHint)
        self.setMinimumSize(900, 500)
        self.resize(1000, 600)
        self.setStyleSheet("background-color: #18181f;")

        self.title_bar = CustomTitleBar(self)
        self.editor = CodeEditor()

        self.menu_bar = QMenuBar()
        self.menu_bar.setStyleSheet("""
            QMenuBar {
                background-color: #18181f;
                color: #ddd;
                font-weight: bold;
                font-size: 12pt;
                spacing: 15px;
            }
            QMenuBar::item:selected {
                background-color: #2a2a3d;
            }
            QMenu {
                background-color: #18181f;
                color: #ddd;
                font-size: 12pt;
            }
            QMenu::item:selected {
                background-color: #264f78;
            }
        """)

        file_menu = self.menu_bar.addMenu("File")
        new_action = QAction("New", self)
        new_action.triggered.connect(self.new_file)
        open_action = QAction("Open...", self)
        open_action.triggered.connect(self.open_file)
        save_action = QAction("Save", self)
        save_action.triggered.connect(self.save_file)
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addActions([new_action, open_action, save_action])
        file_menu.addSeparator()
        file_menu.addAction(exit_action)

        edit_menu = self.menu_bar.addMenu("Edit")
        edit_menu.addAction(QAction("Cut", self, triggered=self.editor.cut))
        edit_menu.addAction(QAction("Copy", self, triggered=self.editor.copy))
        edit_menu.addAction(QAction("Paste", self, triggered=self.editor.paste))
        edit_menu.addAction(QAction("Select All", self, triggered=self.editor.selectAll))

        help_menu = self.menu_bar.addMenu("Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.title_bar)
        layout.addWidget(self.menu_bar)
        layout.addWidget(self.editor)

        self.windowStateChanged = False
        self.old_geometry = self.geometry()

        self.apply_rounded_corners()

    def apply_rounded_corners(self):
        rect = QRectF(self.rect())
        radius = 15.0
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)
        region = QRegion(path.toFillPolygon().toPolygon())
        self.setMask(region)

    def apply_sharp_corners(self):
        self.clearMask()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self.isMaximized():
            self.apply_rounded_corners()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == event.WindowStateChange:
            if self.isMaximized():
                self.apply_sharp_corners()
            else:
                self.apply_rounded_corners()

    def new_file(self):
        self.editor.clear()

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open File", "", "Text Files (*.txt);;All Files (*)")
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self.editor.setPlainText(f.read())
            except Exception as e:
                print(f"Could not open file: {e}")

    def save_file(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save File", "", "Text Files (*.txt);;All Files (*)")
        if path:
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(self.editor.toPlainText())
            except Exception as e:
                print(f"Could not save file: {e}")

    def show_about(self):
        dlg = AboutDialog(self)
        dlg.exec_()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Set application icon
    app.setWindowIcon(QIcon(resource_path("icon.ico")))

    # Load and scale splash image using resource_path
    splash_pix = QPixmap(resource_path("splash.png"))
    if splash_pix.isNull():
        print("Failed to load splash.png")
    else:
        splash_pix = splash_pix.scaled(400, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    splash = QSplashScreen(splash_pix, Qt.WindowStaysOnTopHint)
    splash.setMask(splash_pix.mask())
    splash.show()
    app.processEvents()

    w = MainWindow()

    QTimer.singleShot(1200, splash.close)
    QTimer.singleShot(1200, w.show)

    sys.exit(app.exec_())

