from PyQt4 import QtCore, QtGui

import dat.gui
from dat.gui.data_provenance import DataProvenancePanel
from dat.gui.operations import OperationPanel
from dat.gui.plots import PlotPanel
from dat.gui.variables import VariablePanel
from dat.vistrail_data import VistrailManager

from vistrails.core.application import get_vistrails_application
from vistrails.packages.spreadsheet.spreadsheet_controller import \
    spreadsheetController


class MainWindow(QtGui.QMainWindow):
    """The main window of the DAT application.

    Embeds the VisTrails spreadsheet.
    """
    def __init__(self):
        QtGui.QMainWindow.__init__(self)

        self.setWindowTitle("DAT")

        _ = dat.gui.translate(MainWindow)

        menubar = self.menuBar()

        fileMenu = menubar.addMenu(_("&File"))
        newAction = fileMenu.addAction(_("&New..."))
        self.connect(newAction, QtCore.SIGNAL('triggered()'),
                     self.newFile)
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

        # Spreadsheet hooks
        ss_hooks = dict(
                window_menu_main=False,
                window_menu_view=False,
                window_menu_window=False,

                window_quit_action=False,

                window_create_first_sheet=False,
                tab_create_sheet=True,
                tab_create_sheet_action=VistrailManager.hook_create_tab,
                tab_rename_sheet=True,
                tab_begin_rename_action=VistrailManager.hook_rename_tab_begin,
                tab_end_rename_action=VistrailManager.hook_rename_tab_end,
                tab_close_sheet=True,
                tab_close_sheet_action=VistrailManager.hook_close_tab,
                tab_delete_cell=False,
        )

        # Embed the spreadsheet window as the central widget
        spreadsheetController.set_hooks(ss_hooks)
        self.spreadsheetWindow = spreadsheetController.findSpreadsheetWindow(
                show=False)
        self.setCentralWidget(self.spreadsheetWindow)
        self.spreadsheetWindow.setVisible(True)

        # Create the panels
        # DockWidgetClosable is not permitted
        self._variables = VariablePanel(VistrailManager())
        self._plots = PlotPanel()
        self._operations = OperationPanel()
        self._data_provenance = DataProvenancePanel()

        self.connect(
                self._variables,
                QtCore.SIGNAL('variableSelected(PyQt_PyObject)'),
                self._data_provenance.showVariable)

        def dock_panel(title, widget, pos):
            dock = QtGui.QDockWidget(title)
            dock.setFeatures(QtGui.QDockWidget.DockWidgetMovable |
                              QtGui.QDockWidget.DockWidgetFloatable)
            dock.setWidget(widget)
            self.addDockWidget(pos, dock)
            return dock

        dock_panel(_("Plots"), self._plots,
                   QtCore.Qt.RightDockWidgetArea)
        self._variables_dock = dock_panel(_("Variables"), self._variables,
                                          QtCore.Qt.LeftDockWidgetArea)
        dock_panel(_("Calculator"), self._operations,
                   QtCore.Qt.LeftDockWidgetArea)
        prov_dock = dock_panel(_("Data Provenance"), self._data_provenance,
                               QtCore.Qt.LeftDockWidgetArea)
        self.tabifyDockWidget(self._variables_dock, prov_dock)
        self._variables_dock.raise_()

        get_vistrails_application().register_notification(
                'dat_controller_changed',
                self._controller_changed)

    def _controller_changed(self, controller, new=False):
        self._variables.unregister_notifications()
        self._variables = VariablePanel(VistrailManager(controller))
        self._variables_dock.setWidget(self._variables)
        self.connect(
                self._variables,
                QtCore.SIGNAL('variableSelected(PyQt_PyObject)'),
                self._data_provenance.showVariable)

        is_dat_controller = VistrailManager(controller) is not None
        self._operations.setEnabled(is_dat_controller)
        self._plots.setEnabled(is_dat_controller)

    def newFile(self):
        builderWindow = get_vistrails_application().builderWindow
        view = builderWindow.new_vistrail()
        if view is not None:
            VistrailManager.set_controller(
                    view.get_controller(),
                    register=True)

    def openFile(self):
        builderWindow = get_vistrails_application().builderWindow
        view = builderWindow.open_vistrail_default()
        if view is not None:
            VistrailManager.set_controller(
                    view.get_controller(),
                    register=True)

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
