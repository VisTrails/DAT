from PyQt4 import QtCore, QtGui

from dat import MIMETYPE_DAT_PLOT
from dat.gui.generic import DraggableCategorizedListWidget
from dat.global_data import GlobalManager

from vistrails.core.application import get_vistrails_application
from vistrails.core.packagemanager import get_package_manager


class PlotList(DraggableCategorizedListWidget):
    def buildData(self, item):
        data = QtCore.QMimeData()
        data.setData(
                self._mime_type,
                '%s,%s' % (
                        item.plot.package_identifier, item.plot.name))
        return data


class PlotItem(QtGui.QTreeWidgetItem):
    """An item in the list of plots.

    Displays the 'name' field of the plot.
    """
    def __init__(self, plot, category):
        QtGui.QListWidgetItem.__init__(self, [plot.name])
        self.setToolTip(0, plot.description)
        self.plot = plot
        self.category = category


class PlotPanel(QtGui.QWidget):
    """The panel showing all the known plots.
    """
    def __init__(self):
        QtGui.QWidget.__init__(self)

        self._plots = dict() # Plot -> PlotItem

        layout = QtGui.QVBoxLayout()

        self._list_widget = PlotList(
                self,
                MIMETYPE_DAT_PLOT)
        layout.addWidget(self._list_widget)

        self.setLayout(layout)

        app = get_vistrails_application()
        app.register_notification('dat_new_plot', self.plot_added)
        app.register_notification('dat_removed_plot', self.plot_removed)

        for plot in GlobalManager.plots:
            self.plot_added(plot)

    def plot_added(self, plot):
        pm = get_package_manager()
        package = pm.get_package_by_identifier(plot.package_identifier)
        item = PlotItem(plot, package.name)
        self._plots[plot] = item
        self._list_widget.addItem(item, package.name)

    def plot_removed(self, plot):
        item = self._plots.pop(plot)
        self._list_widget.removeItem(item, item.category)
