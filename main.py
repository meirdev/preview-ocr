import math
import os
import sys
from datetime import datetime

from PIL import Image
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *

import ocr


settings = QSettings("Preview")


class IVGraphicsView(QGraphicsView):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._firstText = None

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.parent().clearSelectedText.emit()

        item = self.itemAt(event.pos())
        if isinstance(item, IVGraphicsRectItem):
            self._firstText = item

        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        item = self.itemAt(event.pos())
        if isinstance(item, IVGraphicsRectItem):
            self.setCursor(Qt.CursorShape.IBeamCursor)

            if self._firstText:
                self.parent().setSelectedText.emit(self._firstText, item)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self.clearFirstText()

        event.accept()

    def clearFirstText(self) -> None:
        self._firstText = None


class IVGraphicsRectItem(QGraphicsRectItem):
    _selectedColor = QColor(100, 167, 255, 50)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._isSelected = False

    def setTextObject(self, value: ocr.Text) -> None:
        self.setData(0, value)

    def getTextObject(self) -> ocr.Text:
        return self.data(0)

    def setSelected(self, selected: bool) -> None:
        self._isSelected = selected

        if selected:
            self.setBrush(self._selectedColor)
        else:
            self.setBrush(Qt.GlobalColor.transparent)

    def isSelected(self) -> bool:
        return self._isSelected


def showFileDialog() -> str | None:
    directory = settings.value("fileDialogDirectory", os.path.expanduser("~"))

    fileName, _ = QFileDialog.getOpenFileName(
        None, "Select Image", directory, "Image Files (*.png *.jpg *.bmp)"
    )

    if fileName:
        settings.setValue("fileDialogDirectory", os.path.dirname(fileName))

        return fileName

    return None


class HLine(QFrame):
    def __init__(self) -> None:
        super().__init__()

        self.setFrameShape(QFrame.Shape.HLine)
        self.setFrameShadow(QFrame.Shadow.Sunken)


class ImageViewer(QMainWindow):
    _fileName: str
    _graphicsPixmapItem: QGraphicsPixmapItem
    _graphicScene: QGraphicsScene
    _graphicsView: IVGraphicsView
    _resizeLoadImage: bool
    _scale: float
    _text: list[ocr.Text]
    _textRectItems: list[IVGraphicsRectItem]

    clearSelectedText = pyqtSignal()
    setSelectedText = pyqtSignal(IVGraphicsRectItem, IVGraphicsRectItem)

    def __init__(self, fileName: str) -> None:
        super().__init__()

        self.setUnifiedTitleAndToolBarOnMac(True)

        self._setupUi()

        self._connectSignals()

        self._loadImage(fileName)

        self.setCentralWidget(self._graphicsView)

    def _addMenuBar(self) -> None:
        menu = self.menuBar()

        menu_file = menu.addMenu("&File")

        action_open = menu_file.addAction("Open...")
        action_open.triggered.connect(self._openFile)

        menu_edit = menu.addMenu("&Edit")

        action_copy = menu_edit.addAction("&Copy")
        action_copy.setShortcut(QKeySequence(QKeySequence.StandardKey.Copy))
        action_copy.triggered.connect(self._copyTextToClipboard)

    def _addTopToolbar(self) -> None:
        toolbar = QToolBar("Top Toolbar")
        toolbar.setIconSize(QSize(16, 16))
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        toolbar.setMovable(False)

        action_info = toolbar.addAction(QIcon("icons/info.svg"), "I&nfo")
        action_info.triggered.connect(self._showFileInfo)

        action_zoom_out = toolbar.addAction(QIcon("icons/zoom-out.svg"), "Zoom &Out")
        action_zoom_out.triggered.connect(self._zoomOut)

        action_zoom_in = toolbar.addAction(QIcon("icons/zoom-in.svg"), "Zoom &In")
        action_zoom_in.triggered.connect(self._zoomIn)

        self.addToolBar(toolbar)

    def _addGraphicsView(self) -> None:
        self._graphicScene = QGraphicsScene()
        self._graphicScene.setBackgroundBrush(Qt.GlobalColor.darkGray)

        self._graphicsView = IVGraphicsView(self._graphicScene, self)

    def _setupUi(self) -> None:
        self._addMenuBar()
        self._addTopToolbar()
        self._addGraphicsView()

    def _connectSignals(self) -> None:
        self.clearSelectedText.connect(self._clearSelectedText)
        self.setSelectedText.connect(self._setSelectedText)

    def _openFile(self) -> None:
        if fileName := showFileDialog():
            self._loadImage(fileName)

    def _showFileInfo(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("General Info")

        layout = QFormLayout()

        fileName = self._fileName
        layout.addRow("File name:", QLabel(fileName))

        size = os.path.getsize(fileName)
        layout.addRow("File size:", QLabel(f"{size:,} bytes"))

        creationDate = datetime.fromtimestamp(os.path.getctime(fileName))
        layout.addRow("Creation date:", QLabel(creationDate.strftime("%c")))

        modificationDate = datetime.fromtimestamp(os.path.getmtime(fileName))
        layout.addRow("Modification date:", QLabel(modificationDate.strftime("%c")))

        layout.addRow(HLine())

        with Image.open(fileName) as image:
            width, height = image.size

        layout.addRow("Image size:", QLabel(f"{width} x {height} pixels"))

        dialog.setLayout(layout)

        dialog.exec()

    def _zoom(self, factor: int) -> None:
        self._scale *= factor

        transform = QTransform()
        transform.scale(self._scale, self._scale)

        self._graphicsView.setTransform(transform)

    def _zoomIn(self) -> None:
        self._zoom(1.25)

    def _zoomOut(self) -> None:
        self._zoom(0.8)

    def _loadImage(self, fileName: str) -> None:
        self._fileName = fileName

        self.setWindowTitle(os.path.basename(fileName))

        self._graphicScene.clear()

        self._graphicsView.clearFirstText()

        image = QImage(fileName)

        self._graphicsPixmapItem = QGraphicsPixmapItem(QPixmap.fromImage(image))
        self._graphicsPixmapItem.setTransformationMode(
            Qt.TransformationMode.SmoothTransformation
        )

        self._graphicScene.addItem(self._graphicsPixmapItem)
        self._graphicScene.setSceneRect(self._graphicsPixmapItem.sceneBoundingRect())

        self._scale = self._getInitScale()

        self._resizeLoadImage = True

        self._updateSize()

        self._doOCR()

    def _updateSize(self) -> None:
        screen = QGuiApplication.primaryScreen()
        screenGeometry = screen.geometry()
        screenWidth, screenHeight = screenGeometry.width(), screenGeometry.height()

        rect = self._graphicsPixmapItem.sceneBoundingRect()
        rectWidth, rectHeight = rect.width(), rect.height()

        scale = self._scale + 0.1

        minWidth = math.ceil(min(screenWidth, rectWidth * scale))
        minHeight = math.ceil(min(screenHeight, rectHeight * scale))

        self.resize(minWidth, minHeight)

    def _doOCR(self) -> None:
        self._text = ocr.get_text(self._fileName)

        ocr.fix_size_and_position(self._text)

        noPen = QPen()
        noPen.setStyle(Qt.PenStyle.NoPen)

        self._textRectItems = []

        for i in self._text:
            rectItem = IVGraphicsRectItem(i.left, i.top, i.width, i.height)
            rectItem.setAcceptHoverEvents(True)
            rectItem.setTextObject(i)
            rectItem.setPen(noPen)

            self._textRectItems.append(rectItem)

            self._graphicScene.addItem(rectItem)

    def _copyTextToClipboard(self) -> None:
        text = [i.getTextObject() for i in self._textRectItems if i.isSelected()]

        QApplication.clipboard().setText(ocr.get_plain_text(text))

    def _setSelectedText(
        self, first: IVGraphicsRectItem, second: IVGraphicsRectItem
    ) -> None:
        start, end = sorted(
            [self._textRectItems.index(first), self._textRectItems.index(second)]
        )
        textReactItemsRange = [
            rect for i, rect in enumerate(self._textRectItems) if start <= i <= end
        ]

        for i in self._textRectItems:
            i.setSelected(i in textReactItemsRange)

    def _clearSelectedText(self) -> None:
        for i in self._textRectItems:
            i.setSelected(False)

    def _getInitScale(self) -> float:
        with Image.open(self._fileName) as image:
            dpi, _ = image.info["dpi"]

        screen = QGuiApplication.primaryScreen()

        return screen.logicalDotsPerInch() / math.ceil(dpi)

    def resizeEvent(self, event: QResizeEvent) -> None:
        if self._resizeLoadImage:
            self._resizeLoadImage = False

            fit = self._scale
        else:
            rect = self._graphicsPixmapItem.sceneBoundingRect()

            fit = min(
                self._graphicsView.viewport().width() / rect.width(),
                self._graphicsView.viewport().height() / rect.height(),
            )

        transform = QTransform()
        transform.scale(fit, fit)

        self._graphicsView.setTransform(transform)

        event.accept()


def main() -> None:
    app = QApplication(sys.argv)

    if fileName := showFileDialog():
        image_viewer = ImageViewer(fileName)
        image_viewer.show()

        app.exec()


if __name__ == "__main__":
    main()
