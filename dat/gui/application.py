import sys
from PyQt4 import QtGui

from dat.gui.window import MainWindow


def start():
    app = QtGui.QApplication(sys.argv)

    mw = MainWindow()
    mw.setVisible(True)

    return app.exec_()
