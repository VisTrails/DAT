from PyQt4 import QtCore, QtGui

from dat import MIMETYPE_DAT_VARIABLE, MIMETYPE_DAT_PLOT
from dat.gui import translate

from vistrails.packages.spreadsheet.spreadsheet_cell import QCellContainer


class Overlay(object):
    background = QtGui.QColor(255, 255, 255, 127)
    ok_pen  = QtGui.QColor(102, 153, 255)
    ok_fill = QtGui.QColor(187, 204, 255)
    no_pen  = QtGui.QColor(255,  51,  51)
    no_fill = QtGui.QColor(255, 170, 170)
    text    = QtGui.QColor(0, 0, 0)

    def draw(self, cellcontainer, qp):
        qp.fillRect(
                0, 0,
                cellcontainer.width(), cellcontainer.height(),
                Overlay.background)


class DropDeniedOverlay(Overlay):
    def draw(self, cellcontainer, qp):
        Overlay.draw(self, cellcontainer, qp)

        qp.setPen(Overlay.no_pen)
        qp.setBrush(Overlay.no_fill)
        qp.drawRect(
                10, 10,
                cellcontainer.width() - 20, cellcontainer.height() - 20)


class PlotDroppingOverlay(Overlay):
    def draw(self, cellcontainer, qp):
        Overlay.draw(self, cellcontainer, qp)

        qp.setPen(Overlay.ok_pen)
        qp.setBrush(Overlay.ok_fill)
        qp.drawRect(
                10, 10,
                cellcontainer.width() - 20, cellcontainer.height() - 20)


class VariableDroppingOverlay(Overlay):
    def draw(self, cellcontainer, qp):
        Overlay.draw(self, cellcontainer, qp)

        # TODO-dat : draw the actual overlay
        qp.setPen(Overlay.text)
        qp.setBrush(QtCore.Qt.NoBrush)
        metrics = qp.fontMetrics()
        ascent = metrics.ascent()
        height = metrics.height()
        y = 5 + ascent
        qp.drawText(5, y, cellcontainer._plot.name + " (")
        for port in cellcontainer._plot.ports:
            y += height
            qp.drawText(20, y, port.name)
        y += height
        qp.drawText(5, y, ")")


class PlotPromptOverlay(Overlay):
    def draw(self, cellcontainer, qp):
        _ = translate(PlotPromptOverlay)

        qp.setPen(Overlay.text)
        qp.setBrush(QtCore.Qt.NoBrush)
        qp.drawText(
                0, 0,
                cellcontainer.width(), cellcontainer.height(),
                QtCore.Qt.AlignCenter,
                _("Drag a plot in this cell"))


class DATCellContainer(QCellContainer):
    def __init__(self, widget=None, parent=None):
        QCellContainer.__init__(self, widget=widget, parent=parent)

        self.setAcceptDrops(True)
        self._overlay = None

        self._plot = None # dat.packages:Plot
        self._variables = []

        self._set_overlay(None)

    def setWidget(self, widget):
        super(DATCellContainer, self).setWidget(widget)
        if widget is not None:
            widget.lower()

    def _set_overlay(self, overlay_class):
        if overlay_class is None:
            # Default overlay
            if self.widget() is None and self._plot is not None:
                self._set_overlay(VariableDroppingOverlay)
            elif self.widget() is None:
                self._set_overlay(PlotPromptOverlay)
            elif self._overlay is not None:
                self._overlay = None
                self.repaint()

        elif not self._overlay or not isinstance(self._overlay, overlay_class):
            self._overlay = overlay_class()
            self.repaint()

    def dragEnterEvent(self, event):
        mimeData = event.mimeData()
        if mimeData.hasFormat(MIMETYPE_DAT_VARIABLE):
            if self._plot is None:
                # We should ignore the drop here. That would make sense, and
                # display the correct mouse pointer
                # We can't though, because Qt would stop sending drag and drop
                # events
                # We still refuse the QDropEvent when the drop happens
                self._set_overlay(DropDeniedOverlay)
            else:
                # TODO-dat : target a specific parameter
                self._set_overlay(VariableDroppingOverlay)
        elif mimeData.hasFormat(MIMETYPE_DAT_PLOT):
            self._set_overlay(PlotDroppingOverlay)
        else:
            event.ignore()
            return
        event.accept()

    def dragMoveEvent(self, event):
        mimeData = event.mimeData()
        if (mimeData.hasFormat(MIMETYPE_DAT_VARIABLE) or
                mimeData.hasFormat(MIMETYPE_DAT_PLOT)):
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
            # TODO-dat : update overlay
            # event.pos()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self._set_overlay(None)

    def dropEvent(self, event):
        mimeData = event.mimeData()

        if mimeData.hasFormat(MIMETYPE_DAT_VARIABLE):
            if self._plot is None:
                event.ignore()
            else:
                event.accept()
                # TODO-dat : add/change a variable to this cell

        elif mimeData.hasFormat(MIMETYPE_DAT_PLOT):
            event.accept()
            # TODO-dat : change the plot in this cell
            self._plot = mimeData.plot
            self._variables = []
            # Deleting a plot must update the pipeline infos in the spreadsheet
            # tab
            # StandardWidgetSheetTabInterface#deleteCell()

        else:
            event.ignore()

        self._set_overlay(None)

    def paintEvent(self, event):
        QCellContainer.paintEvent(self, event)

        if self._overlay:
            self._overlay.draw(self, QtGui.QPainter(self))
