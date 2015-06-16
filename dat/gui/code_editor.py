from PyQt4 import QtCore, QtGui

from dat.gui import translate

from vistrails.gui.modules.python_source_configure import PythonEditor


class CodeEditor(QtGui.QWidget):
    def __init__(self, cellcontainer):
        QtGui.QWidget.__init__(self, cellcontainer, QtCore.Qt.Window)
        self._cell = cellcontainer
        self._cell.set_code_editor(self)
        self.show()

        _ = translate(CodeEditor)

        self._editor = PythonEditor()

        buttons = QtGui.QHBoxLayout()
        buttons.addStretch(1)
        cancel_button = QtGui.QPushButton(_("Cancel"))
        self.connect(cancel_button, QtCore.SIGNAL('clicked()'),
                     self.close)
        buttons.addWidget(cancel_button)
        self._execute_button = QtGui.QPushButton(_("Update plot"))
        self._execute_button.setEnabled(False)
        self.connect(self._execute_button, QtCore.SIGNAL('clicked()'),
                     self.execute)
        buttons.addWidget(self._execute_button)

        layout = QtGui.QVBoxLayout()
        layout.addWidget(self._editor)
        layout.addLayout(buttons)
        self.setLayout(layout)

        self.contentsUpdated()

    def closeEvent(self, event):
        event.accept()
        self.deleteLater()
        self._cell.set_code_editor(None)

    def contentsUpdated(self):
        self._editor.setPlainText("if __name__ == '__main__':\n"
                                  "    print \"TODO\"")

    def execute(self):
        pass
