from PyQt4 import QtCore, QtGui

from dat import MIMETYPE_DAT_VARIABLE, MIMETYPE_DAT_PLOT
from dat.gui import translate
from dat.manager import Manager

from vistrails.packages.spreadsheet.spreadsheet_cell import QCellContainer


class Overlay(object):
    """Base class for the cell overlays.
    """

    def __init__(self, cellcontainer, mimeData):
        self._cell = cellcontainer

    background = QtGui.QColor(255, 255, 255, 127)
    ok_pen  = QtGui.QColor(102, 153, 255)
    ok_fill = QtGui.QColor(187, 204, 255)
    no_pen  = QtGui.QColor(255,  51,  51)
    no_fill = QtGui.QColor(255, 170, 170)
    text    = QtGui.QColor(0, 0, 0)

    def draw(self, qp):
        qp.fillRect(
                0, 0,
                self._cell.width(), self._cell.height(),
                Overlay.background)

    def set_mouse_position(self, x, y):
        pass


class VariableDropEmptyCell(Overlay):
    """Used when dragging a variable over a cell without a plot.

    A plot must be dropped first, so that the types of the parameters are
    known.
    """

    def draw(self, qp):
        _ = translate(VariableDropEmptyCell)

        Overlay.draw(self, qp)

        qp.setPen(Overlay.no_pen)
        qp.setBrush(Overlay.no_fill)
        qp.drawRect(
                10, 10,
                self._cell.width() - 20, self._cell.height() - 20)

        qp.drawText(
                10, 10,
                self._cell.width() - 20, self._cell.height() - 20,
                QtCore.Qt.AlignCenter | QtCore.Qt.TextWordWrap,
                _("You need to drag a plot first"))


class PlotDroppingOverlay(Overlay):
    """Shown when dragging a plot in a cell.

    Just provides feedback for the user.
    """

    def __init__(self, cellcontainer, mimeData):
        _ = translate(PlotDroppingOverlay)

        Overlay.__init__(self, cellcontainer, mimeData)

        if cellcontainer._plot is None:
            text = _("Drop here to add a {plotname} to this cell")
        else:
            text = _("Drop here to replace this plot with a new {plotname}")
        self._text = text.format(
                plotname=mimeData.plot.name)

    def draw(self, qp):
        Overlay.draw(self, qp)

        qp.setPen(Overlay.ok_pen)
        qp.setBrush(Overlay.ok_fill)
        qp.drawRect(
                10, 10,
                self._cell.width() - 20, self._cell.height() - 20)

        qp.drawText(
                10, 10,
                self._cell.width() - 20, self._cell.height() - 20,
                QtCore.Qt.AlignCenter | QtCore.Qt.TextWordWrap,
                self._text)


class VariableDroppingOverlay(Overlay):
    """The main overlay.

    Displays targets for each parameter, according to the current plot, and
    type-checks them.
    """

    def __init__(self, cellcontainer, mimeData):
        Overlay.__init__(self, cellcontainer, mimeData)

        # Type-checking, so we can show which parameters are suitable to
        # receive the drop
        if not mimeData or not mimeData.hasFormat(MIMETYPE_DAT_VARIABLE):
            self._compatible_ports = None
        else:
            varname = str(mimeData.data(MIMETYPE_DAT_VARIABLE))
            variable = Manager().get_variable(varname)
            self._compatible_ports = [issubclass(variable.type, port.type)
                                      for port in self._cell._plot.ports]

    def draw(self, qp):
        Overlay.draw(self, qp)

        qp.setPen(Overlay.text)
        qp.setBrush(QtCore.Qt.NoBrush)
        metrics = qp.fontMetrics()
        ascent = metrics.ascent()
        height = metrics.height()
        y = 5 + ascent
        qp.drawText(5, y, self._cell._plot.name + " (")
        for i, port in enumerate(self._cell._plot.ports):
            y += height
            if self._compatible_ports:
                if self._compatible_ports[i]:
                    qp.setPen(Overlay.ok_pen)
                    qp.setBrush(Overlay.ok_fill)
                else:
                    qp.setPen(Overlay.no_pen)
                    qp.setBrush(Overlay.no_fill)
                qp.drawRect(20, y - ascent, 50, height)
            qp.setPen(Overlay.text)
            qp.setBrush(QtCore.Qt.NoBrush)
            qp.drawText(20, y, port.name)
        y += height
        qp.drawText(5, y, ")")

    def set_mouse_position(self, x, y):
        # TODO-dat : update overlay (target a parameter)
        pass


class PlotPromptOverlay(Overlay):
    """Default content of the overlayed cells.

    Simply displays a prompt asking the user to drop a plot in the cell.
    """

    def draw(self, qp):
        _ = translate(PlotPromptOverlay)

        qp.setPen(Overlay.text)
        qp.setBrush(QtCore.Qt.NoBrush)
        qp.drawText(
                10, 10,
                self._cell.width() - 20, self._cell.height() - 20,
                QtCore.Qt.AlignCenter | QtCore.Qt.TextWordWrap,
                _("Drag a plot in this cell"))


class DATCellContainer(QCellContainer):
    """Cell container used in the spreadsheet.

    This is created by the spreadsheet for each cell, thus allowing us to tap
    into its behavior.
    It adds an overlay feature to the spreadsheet's cells and handles drops of
    variables and plots.
    """

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

    def _set_overlay(self, overlay_class, mimeData=None):
        if overlay_class is None:
            # Default overlay
            if self.widget() is None and self._plot is not None:
                self._set_overlay(VariableDroppingOverlay)
            elif self.widget() is None:
                self._set_overlay(PlotPromptOverlay)
            elif self._overlay is not None:
                self._overlay = None
                self.repaint()

        else:
            self._overlay = overlay_class(self, mimeData)
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
                self._set_overlay(VariableDropEmptyCell, mimeData)
            else:
                # TODO-dat : target a specific parameter
                self._set_overlay(VariableDroppingOverlay, mimeData)
        elif mimeData.hasFormat(MIMETYPE_DAT_PLOT):
            self._set_overlay(PlotDroppingOverlay, mimeData)
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
            self._overlay.set_mouse_position(event.pos().x(), event.pos().y())
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
            self._overlay.draw(QtGui.QPainter(self))
