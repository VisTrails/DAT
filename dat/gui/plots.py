from PyQt4 import QtGui

from dat.gui.lists import DraggableListWidget
import dat.manager


class PlotItem(QtGui.QListWidgetItem):
    def __init__(self, plot):
        QtGui.QListWidgetItem.__init__(self, plot.name)
        self.plot = plot


class PlotPanel(QtGui.QWidget):
    def __init__(self):
        super(PlotPanel, self).__init__()

        layout = QtGui.QVBoxLayout()

        self._list_widget = DraggableListWidget(self, 'X-Vistrails/DATPlot')
        layout.addWidget(self._list_widget)

        self.setLayout(layout)

        dat.manager.Manager().add_plot_observer((self.plot_added,
                                                 self.plot_removed))
        for plot in dat.manager.Manager().plots:
            self.plot_added(plot)

    def plot_added(self, plot):
        self._list_widget.addItem(PlotItem(plot))

    def plot_removed(self, plot):
        item = 0
        while item < self._list_widget.count():
            if self._list_widget.item(item).plot is plot:
                self._list_widget.takeItem(item)
            else:
                item += 1
