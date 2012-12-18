from PyQt4 import QtCore, QtGui

from vistrails.packages.spreadsheet.spreadsheet_cell import QCellContainer


class DATCellContainer(QCellContainer):
    def __init__(self, widget=None, parent=None):
        QCellContainer.__init__(self, widget=widget, parent=parent)

        self.setAcceptDrops(True)

        # TODO-dat : actual overlay
        self._overlay = QtGui.QLabel("!!! DRAGGING !!!", self)
        self._overlay.setVisible(False)

    def setWidget(self, widget):
        super(DATCellContainer, self).setWidget(widget)
        if widget is not None:
            widget.lower()

    def resizeEvent(self, event):
        # Manual layout of the overlay
        self._overlay.setGeometry(0, 0, self.width(), self.height())
        super(DATCellContainer, self).resizeEvent(event)

    def showDraggingOverlay(self):
        self._overlay.setVisible(True)

    def hideDraggingOverlay(self):
        self._overlay.setVisible(False)

    def dragEnterEvent(self, event):
        mimeData = event.mimeData()
        if (True or mimeData.hasFormat('X-Vistrails/DATVariable') or
                mimeData.hasFormat('X-Vistrails/DATPlot')):
            event.accept()
            self.showDraggingOverlay()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        mimeData = event.mimeData()
        if (True or mimeData.hasFormat('X-Vistrails/DATVariable') or
                mimeData.hasFormat('X-Vistrails/DATPlot')):
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
            # TODO-dat : update overlay
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.hideDraggingOverlay()

    def dropEvent(self, event):
        self.hideDraggingOverlay()
        mimeData = event.mimeData()

        if mimeData.hasFormat('X-Vistrails/DATVariable'):
            event.accept()
            # TODO-dat : add/change a variable to this cell

        elif mimeData.hasFormat('X-Vistrails/DATPlot'):
            event.accept()
            # TODO-dat : change the plot in this cell

        else:
            event.ignore()
