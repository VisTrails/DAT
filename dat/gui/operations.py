from PyQt4 import QtCore, QtGui

from dat.global_data import GlobalManager
from dat.gui import translate
from dat.gui.generic import ConsoleWidget, SingleLineTextEdit
from dat.operations import is_operator, perform_operation, \
    InvalidOperation, OperationWarning
from dat.utils import bisect, catch_warning

from vistrails.core.application import get_vistrails_application


class MarkerHighlighterLineEdit(SingleLineTextEdit):
    def __init__(self):
        SingleLineTextEdit.__init__(self)
        self.__changing = False
        self.setUndoRedoEnabled(False) # FIXME : _highlight breaks undo :(
        self.connect(self, QtCore.SIGNAL('textChanged()'), self._highlight)

    def _highlight(self):
        if self.__changing:
            return
        self.__changing = True
        try:
            pos = self.textCursor().position()
            text = str(self.toPlainText())
            text = text.replace('<', '&lt;')
            text = text.replace('>', '&gt;')
            text = text.replace(
                    '&lt;?&gt;',
                    '<span style="background-color: #99F;">&lt;?&gt;</span>')
            self.setHtml(text)
            cursor = self.textCursor()
            cursor.setPosition(pos)
            self.setTextCursor(cursor)
        finally:
            self.__changing = False


class OperationPanel(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)

        _ = translate(OperationPanel)

        self._operations = dict() # name -> set([operations])

        layout = QtGui.QVBoxLayout()

        self._console = ConsoleWidget()
        layout.addWidget(self._console)

        layout.addWidget(QtGui.QLabel(_("Enter a command and press return")))

        self._input_line = MarkerHighlighterLineEdit()
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
            append = '<?> ' + text + ' <?>'
            pos = (-10, 3)
        else:
            append = text + '()'
            pos = (-2, 0)
        self._input_line.setText(self._input_line.text() + append)
        if pos[0] < 0:
            pos = (len(str(self._input_line.text())) + pos[0] + 1, pos[1])
        self._input_line.setFocus()
        self._input_line.setSelection(*pos)

    def _show_error(self, message, category, filename, lineno,
            file=None, line=None):
        self._console.add_error(message[0])

    def execute_line(self):
        text = str(self._input_line.text())
        try:
            self._console.add_line(text)
            with catch_warning(OperationWarning, handle=self._show_error):
                perform_operation(text)
            self._input_line.setText('')
        except InvalidOperation, e:
            if e.fix is not None:
                self._input_line.setText(e.fix)
            if e.select is not None:
                self._input_line.setSelection(*e.select)
            self._console.add_error(e.message)
