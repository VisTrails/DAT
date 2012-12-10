from PyQt4 import QtGui


class PlotPanel(QtGui.QWidget):
    def __init__(self):
        super(PlotPanel, self).__init__()

        layout = QtGui.QVBoxLayout()

        self._list_widget = QtGui.QListWidget(self)
        self._list_widget.addItem("Plot1")
        self._list_widget.addItem("Plot2")
        self._list_widget.addItem("Plot3")
        layout.addWidget(self._list_widget)

        self.setLayout(layout)
