from PyQt4 import QtGui

from dat.gui.generic import ConsoleWidget


class OperationPanel(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)

        layout = QtGui.QVBoxLayout()

        self._console = ConsoleWidget()
        layout.addWidget(self._console)

        self._input_line = QtGui.QLineEdit()
        layout.addWidget(self._input_line)

        self._list = QtGui.QListWidget()
        layout.addWidget(self._list)

        self.setLayout(layout)
