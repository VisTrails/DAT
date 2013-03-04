from PyQt4 import QtCore, QtGui

from dat.gui import translate
from dat.gui.generic import ConsoleWidget
from dat.operations import is_operator, perform_operation, InvalidExpression
from dat.utils import bisect
from dat.vistrail_data import VistrailManager

from vistrails.core.application import get_vistrails_application
from dat.global_data import GlobalManager


class OperationPanel(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)

        _ = translate(OperationPanel)

        self._operations = dict() # name -> set([operations])

        layout = QtGui.QVBoxLayout()

        self._console = ConsoleWidget()
        layout.addWidget(self._console)

        layout.addWidget(QtGui.QLabel(_("Enter a command and press return")))

        self._input_line = QtGui.QLineEdit()
        self.connect(self._input_line, QtCore.SIGNAL('returnPressed()'),
                     self.execute_line)
        layout.addWidget(self._input_line)

        layout.addWidget(QtGui.QLabel(_("Available operations:")))

        self._list = QtGui.QListWidget()
        self._list.setSelectionMode(QtGui.QAbstractItemView.NoSelection)
        self.connect(
                self._list,
                QtCore.SIGNAL('itemClicked(QListWidgetItem*)'),
                self.operation_clicked)
        layout.addWidget(self._list)

        self.setLayout(layout)

        app = get_vistrails_application()
        app.register_notification('dat_new_operation', self.operation_added)
        app.register_notification('dat_removed_operation',
                                  self.operation_removed)

        for operation in GlobalManager.variable_operations:
            self.operation_added(operation)

    def operation_added(self, operation):
        try:
            self._operations[operation.name].add(operation)
        except KeyError:
            self._operations[operation.name] = set([operation])

            pos = bisect(
                    self._list.count(),
                    lambda i: str(self._list.item(i).text()),
                    operation.name)
            if pos >= 1 and pos - 1 < self._list.count():
                if str(self._list.item(pos-1).text()) == operation.name:
                    return
            self._list.insertItem(pos, operation.name)

    def operation_removed(self, operation):
        ops = self._operations[operation.name]
        ops.remove(operation)
        if not ops:
            del self._operations[operation.name]
            pos = bisect(
                    self._list.count(),
                    lambda i: str(self._list.item(i).text()),
                    operation.name)
            self._list.takeItem(pos-1)

    def operation_clicked(self, item):
        text = str(item.text())
        if is_operator(text):
            append = '? ' + text + ' ?'
            pos = (-6, 1)
        else:
            append = text + '()'
            pos = (-2, 0)
        self._input_line.setText(self._input_line.text() + append)
        if pos[0] < 0:
            pos = (len(str(self._input_line.text())) + pos[0] + 1, pos[1])
        self._input_line.setFocus()
        if pos[1] == 0:
            self._input_line.setCursorPosition(pos[0])
        else:
            self._input_line.setSelection(*pos)

    def execute_line(self):
        text = str(self._input_line.text())
        try:
            perform_operation(text)
            self._console.add_line("Execute %r" % text)
            self._console.add_error("Not implemented")
            self._input_line.setText('')
        except InvalidExpression, e:
            if e.fix is not None:
                self._input_line.setText(e.fix)
            if e.select is not None:
                self._input_line.setSelection(*e.select)
