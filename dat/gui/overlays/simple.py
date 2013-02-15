from PyQt4 import QtCore

from dat.gui import translate
from dat.gui.overlays import Overlay


class PlotPromptOverlay(Overlay):
    """Default content of the overlayed cells.

    Simply displays a prompt asking the user to drop a plot in the cell.
    """

    def draw(self, qp):
        Overlay.draw(self, qp)

        _ = translate(PlotPromptOverlay)

        qp.setPen(Overlay.text)
        qp.setBrush(QtCore.Qt.NoBrush)
        qp.drawText(
                10, 10,
                self.width() - 20, self.height() - 20,
                QtCore.Qt.AlignCenter | QtCore.Qt.TextWordWrap,
                _("Drag a plot in this cell"))


class VariableDropEmptyCell(Overlay):
    """Used when dragging a variable over a cell without a plot.

    A plot must be dropped first, so that the types of the parameters are
    known.
    """

    def __init__(self, cellcontainer, mimeData):
        Overlay.__init__(self, cellcontainer)

    def draw(self, qp):
        _ = translate(VariableDropEmptyCell)

        Overlay.draw(self, qp)

        qp.setPen(Overlay.no_pen)
        qp.setBrush(Overlay.no_fill)
        qp.drawRect(
                10, 10,
                self.width() - 20, self.height() - 20)

        qp.drawText(
                10, 10,
                self.width() - 20, self.height() - 20,
                QtCore.Qt.AlignCenter | QtCore.Qt.TextWordWrap,
                _("You need to drag a plot first"))


class PlotDroppingOverlay(Overlay):
    """Shown when dragging a plot in a cell.

    Just provides feedback for the user.
    """

    def __init__(self, cellcontainer, mimeData):
        _ = translate(PlotDroppingOverlay)

        Overlay.__init__(self, cellcontainer)

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
                self.width() - 20, self.height() - 20)

        qp.drawText(
                10, 10,
                self.width() - 20, self.height() - 20,
                QtCore.Qt.AlignCenter | QtCore.Qt.TextWordWrap,
                self._text)
