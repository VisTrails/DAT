from PyQt4 import QtCore, QtGui

import dat.gui
from dat.vistrail_data import VistrailManager
from dat.gui.plots import PlotPanel
from dat.gui.variables import VariablePanel

from vistrails.core.application import get_vistrails_application
from vistrails.packages.spreadsheet.spreadsheet_controller import spreadsheetController


class MainWindow(QtGui.QMainWindow):
    """The main window of the DAT application.

    Embeds the VisTrails spreadsheet.
    """
    def __init__(self):
        super(MainWindow, self).__init__()

        self.setWindowTitle("DAT")

        _ = dat.gui.translate(MainWindow)

        menubar = self.menuBar()

        fileMenu = menubar.addMenu(_("&File"))
        openAction = fileMenu.addAction(_("&Open..."))
        self.connect(openAction, QtCore.SIGNAL('triggered()'),
                     self.openFile)
        saveAction = fileMenu.addAction(_("&Save"))
        self.connect(saveAction, QtCore.SIGNAL('triggered()'),
                     self.saveFile)
        saveAsAction = fileMenu.addAction(_("Save &as..."))
        self.connect(saveAsAction, QtCore.SIGNAL('triggered()'),
                     self.saveAsFile)
        fileMenu.addSeparator()
        quitAction = fileMenu.addAction(_("&Quit"))
        self.connect(quitAction, QtCore.SIGNAL('triggered()'),
                     self.quitApplication)

        viewMenu = menubar.addMenu(_("&View"))
        showBuilderAction = viewMenu.addAction(_("Show &builder window"))
        self.connect(showBuilderAction, QtCore.SIGNAL('triggered()'),
                     get_vistrails_application().showBuilderWindow)

        # Embed the spreadsheet window as the central widget
        self.spreadsheetWindow = spreadsheetController.findSpreadsheetWindow(
                show=False,
                flags=0)
        self.setCentralWidget(self.spreadsheetWindow)
        self.spreadsheetWindow.setVisible(True)

        # Create the panels
        # DockWidgetClosable is not permitted
        self._variables = VariablePanel(VistrailManager())
        self._plots = PlotPanel()

        plots = QtGui.QDockWidget(_("Plots"))
        plots.setFeatures(QtGui.QDockWidget.DockWidgetMovable |
                          QtGui.QDockWidget.DockWidgetFloatable)
        plots.setWidget(self._plots)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, plots)
        self._variables_dock = QtGui.QDockWidget(_("Variables"))
        self._variables_dock.setFeatures(QtGui.QDockWidget.DockWidgetMovable |
                                         QtGui.QDockWidget.DockWidgetFloatable)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self._variables_dock)
        self._variables_dock.setWidget(self._variables)

        get_vistrails_application().register_notification(
                'dat_controller_changed',
                self._controller_changed)

    def _controller_changed(self, controller, new=False):
        self._variables.unregister_notifications()
        self._variables = VariablePanel(VistrailManager(controller))
        self._variables_dock.setWidget(self._variables)

    def openFile(self):
        get_vistrails_application().builderWindow.open_vistrail_default()

    def saveFile(self):
        from vistrails.core.db.locator import DBLocator, FileLocator
        bw = get_vistrails_application().builderWindow
        bw.get_current_view().save_vistrail(
                bw.dbDefault and DBLocator or FileLocator())

    def saveAsFile(self):
        from vistrails.core.db.locator import DBLocator, FileLocator
        bw = get_vistrails_application().builderWindow
        bw.get_current_view().save_vistrail_as(
                bw.dbDefault and DBLocator or FileLocator())

    def closeEvent(self, event):
        if not self.quitApplication():
            event.ignore()

    def quitApplication(self):
        return get_vistrails_application().try_quit()
