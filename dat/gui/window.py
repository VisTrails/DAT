from PyQt4 import QtCore, QtGui

import dat.gui
from dat.gui.variables import VariablePanel
from dat.gui.plots import PlotPanel


class MainWindow(QtGui.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()

        self.setWindowTitle("DAT")

        _ = dat.gui.translate(MainWindow)

        menubar = self.menuBar()
        fileMenu = menubar.addMenu(_("menu1"))
        quitAction = fileMenu.addAction(_("&Quit"))
        self.connect(quitAction, QtCore.SIGNAL("triggered()"),
                     QtGui.qApp, QtCore.SLOT("quit()"))

        spreadsheet_placeholder = QtGui.QLabel("TODO : spreadsheet here")
        spreadsheet_placeholder.setStyleSheet(
                "QLabel { background-color : white; }")
        self.setCentralWidget(spreadsheet_placeholder)

        self._variables = VariablePanel()
        self._plots = PlotPanel()

        plots = QtGui.QDockWidget(_("Plots"))
        plots.setFeatures(QtGui.QDockWidget.DockWidgetMovable |
                          QtGui.QDockWidget.DockWidgetFloatable)
        plots.setWidget(self._plots)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, plots)
        variables = QtGui.QDockWidget(_("Variables"))
        variables.setFeatures(QtGui.QDockWidget.DockWidgetMovable |
                              QtGui.QDockWidget.DockWidgetFloatable)
        variables.setWidget(self._variables)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, variables)
