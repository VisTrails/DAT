from PyQt4 import QtGui


class Overlay(QtGui.QWidget):
    """Base class for the cell overlays.
    """

    def __init__(self, cellcontainer, overlayed=True, **kwargs):
        QtGui.QWidget.__init__(self, cellcontainer)
        self.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding,
                           QtGui.QSizePolicy.MinimumExpanding)
        self._cell = cellcontainer

    # Background of all overlay (translucent, on top of the cell's content)
    background = QtGui.QColor(255, 255, 255, 200)
    error_background = QtGui.QColor(255, 127, 127, 200)
    # Accepting a drop
    ok_pen = QtGui.QColor(102, 153, 255)
    ok_fill = QtGui.QColor(187, 204, 255)
    # Denying a drop
    no_pen = QtGui.QColor(255, 51, 51)
    no_fill = QtGui.QColor(255, 170, 170)
    # Hovered
    targeted = QtGui.QColor(255, 255, 255)
    # Text (black)
    text = QtGui.QColor(0, 0, 0)

    def draw(self, qp):
        if self._cell.has_error():
            color = Overlay.error_background
        else:
            color = Overlay.background
        qp.fillRect(
                0, 0,
                self.width(), self.height(),
                color)

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        self.draw(qp)

    def set_mouse_position(self, x, y):
        pass


from dat.gui.overlays.simple import PlotPromptOverlay, VariableDropEmptyCell, \
    PlotDroppingOverlay
from dat.gui.overlays.variable_dropping import VariableDroppingOverlay
from dat.gui.overlays.plot_config import PlotConfigOverlay, \
    DefaultPlotConfigOverlay


__all__ = ['Overlay', 'PlotPromptOverlay', 'VariableDropEmptyCell',
           'PlotDroppingOverlay', 'VariableDroppingOverlay',
           'PlotConfigOverlay', 'DefaultPlotConfigOverlay']
