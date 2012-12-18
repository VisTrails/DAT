from PyQt4 import QtGui

from dat.gui.lists import DraggableListWidget


class PlotPanel(QtGui.QWidget):
    def __init__(self):
        super(PlotPanel, self).__init__()

        layout = QtGui.QVBoxLayout()

        self._list_widget = DraggableListWidget(self, 'X-Vistrails/DATPlot')
        self._list_widget.addItem("Plot1")
        self._list_widget.addItem("Plot2")
        self._list_widget.addItem("Plot3")
        layout.addWidget(self._list_widget)

        self.setLayout(layout)
