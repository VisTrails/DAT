import re
from PyQt4 import QtCore, QtGui

from dat import MIMETYPE_DAT_VARIABLE, variable_format
from dat.global_data import GlobalManager
from dat.gui import get_icon, translate
from dat.gui.generic import CategorizedListWidget, ConsoleWidget, \
    SingleLineTextEdit
from dat.operations import is_operator, perform_operation, \
    InvalidOperation, OperationWarning
from dat.utils import catch_warning
from dat.vistrail_data import VistrailManager

from vistrails.core.application import get_vistrails_application
from vistrails.core.packagemanager import get_package_manager


class MarkerHighlighterLineEdit(SingleLineTextEdit):
    def __init__(self):
        SingleLineTextEdit.__init__(self)
        self.__changing = False
        self.setUndoRedoEnabled(False) # FIXME : _highlight breaks undo :(
        self.connect(self, QtCore.SIGNAL('textChanged()'), self._highlight)
        self.setTabChangesFocus(True)

    _marker_pattern = re.compile(r'<(%s)>' % variable_format)
    _html_marker_pattern = re.compile(r'&lt;(%s)&gt;' % variable_format)

    def _highlight(self):
        if self.__changing:
            return
        self.__changing = True
        try:
            pos = self.textCursor().position()
            text = str(self.toPlainText())
            text = text.replace('&', '&amp;')
            text = text.replace('<', '&lt;')
            text = text.replace('>', '&gt;')
            text = text.replace(' ', '&nbsp;')
            text = MarkerHighlighterLineEdit._html_marker_pattern.sub(
                    '<span style="background-color: #99F;">&lt;\\1&gt;</span>',
                    text)
            self.setHtml(text)
            cursor = self.textCursor()
            cursor.setPosition(pos)
            self.setTextCursor(cursor)
        finally:
            self.__changing = False

    def focusNextPrevChild(self, forward):
        cursor = self.textCursor()
        text = str(self.toPlainText())
        if forward:
            marker = MarkerHighlighterLineEdit._marker_pattern.search(
                    text, cursor.selectionEnd())
            if marker is not None:
                marker = marker.span()
        else:
            # Find last match
            marker = None
            pos = 0
            while True:
                m = MarkerHighlighterLineEdit._marker_pattern.search(
                        text, pos, cursor.selectionStart())
                if m is not None:
                    marker = m.span()
                    pos = marker[1]
                else:
                    break

        if marker is not None:
            self.setSelection(marker[0], marker[1] - marker[0])
            return True
        else:
            if forward:
                self.setSelection(cursor.selectionEnd())
            else:
                self.setSelection(cursor.selectionStart())
            return super(MarkerHighlighterLineEdit, self).focusNextPrevChild(forward)

    def focus_first_marker(self):
        text = str(self.toPlainText())
        marker = MarkerHighlighterLineEdit._marker_pattern.search(text)
        if marker is not None:
            marker = marker.span()
            self.setSelection(marker[0], marker[1] - marker[0])

    def has_markers(self):
        text = str(self.toPlainText())
        match = MarkerHighlighterLineEdit._marker_pattern.search(text)
        return match is not None

    def replace_first_marker(self, value):
        text = str(self.toPlainText())
        text = MarkerHighlighterLineEdit._marker_pattern.sub(
                value,
                text,
                1)
        self.setText(text)


class OperationItem(QtGui.QTreeWidgetItem):
    def __init__(self, operation, category, wizard=False):
        if is_operator(operation.name):
            _ = translate(OperationItem)
            name = _("operator {op}").format(op=operation.name)
        else:
            name = operation.name
        QtGui.QTreeWidgetItem.__init__(self, [name])
        if wizard:
            self.setIcon(1, get_icon('operation_wizard.png'))
        self.operation = operation
        self.category = category


class OperationPanel(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)

        _ = translate(OperationPanel)

        self.setAcceptDrops(True)

        self._operations = dict() # VariableOperation -> OperationItem

        layout = QtGui.QVBoxLayout()

        self._console = ConsoleWidget()
        layout.addWidget(self._console)

        layout.addWidget(QtGui.QLabel(_("Enter a command and press return")))

        self._input_line = MarkerHighlighterLineEdit()
        self.connect(self._input_line, QtCore.SIGNAL('returnPressed()'),
                     self.execute_line)
        layout.addWidget(self._input_line)

        layout.addWidget(QtGui.QLabel(_("Available operations:")))

        self._list = CategorizedListWidget(columns=2)
        self._list.setSelectionMode(QtGui.QAbstractItemView.NoSelection)
        self._list.header().setResizeMode(QtGui.QHeaderView.Stretch)
        self.connect(
                self._list,
                QtCore.SIGNAL('itemClicked(QTreeWidgetItem*, int)'),
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
        pm = get_package_manager()
        package = pm.get_package_by_identifier(operation.package_identifier)
        item = OperationItem(operation, package.name,
                             operation.wizard is not None)
        self._operations[operation] = item
        self._list.addItem(item, package.name)

    def operation_removed(self, operation):
        item = self._operations.pop(operation)
        self._list.removeItem(item, item.category)

    def dragEnterEvent(self, event):
        mimeData = event.mimeData()
        if (mimeData.hasFormat(MIMETYPE_DAT_VARIABLE) and
                self._input_line.has_markers() and
                VistrailManager().get_variable(
                    str(mimeData.data(MIMETYPE_DAT_VARIABLE))) is not None):
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        mimeData = event.mimeData()
        if mimeData.hasFormat(MIMETYPE_DAT_VARIABLE):
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        mimeData = event.mimeData()
        if (mimeData.hasFormat(MIMETYPE_DAT_VARIABLE) and
                self._input_line.has_markers()):
            varname = str(mimeData.data(MIMETYPE_DAT_VARIABLE))
            variable = VistrailManager().get_variable(varname)
            if variable is not None:
                self._input_line.replace_first_marker(varname)
                event.accept()
                self._input_line.setFocus(QtCore.Qt.MouseFocusReason)
                self._input_line.focus_first_marker()
                return
        event.ignore()

    def operation_clicked(self, item, column=0):
        if not isinstance(item, OperationItem):
            return
        if column == 0 and item.operation.usable_in_command:
            self._insert_operation(item.operation)
        elif column == 1:
            if item.operation.wizard is not None:
                wizard = item.operation.wizard(self)
                r = wizard.exec_()
                if r == QtGui.QDialog.Accepted:
                    if wizard.command:
                        self.execute(wizard.command)

    def _insert_operation(self, operation):
        text = operation.name
        if is_operator(text):
            append = '\0<%s>\0 %s <%s>' % (
                    operation.parameters[0].name,
                    text,
                    operation.parameters[1].name)
        else:
            append = text + '('
            if operation.parameters:
                append += '\0<%s>\0' % operation.parameters[0].name
                for param in operation.parameters[1:]:
                    append += ', <%s>' % param.name
                append += ')'
            else:
                append += '\0\0)'

        text = str(self._input_line.text())
        cursor = self._input_line.textCursor()
        # If a placeholder is selected
        selection = str(cursor.selectedText())
        marker = MarkerHighlighterLineEdit._marker_pattern.match(selection)
        if marker is not None and marker.end() == len(selection):
            # Replace it with the new operation
            text = (
                    text[:self._input_line.textCursor().selectionStart()] +
                    append +
                    text[self._input_line.textCursor().selectionEnd()])
        # Else
        else:
            # Just append
            text = text + append
        pos = text.find('\0')
        pos = pos, text.find('\0', pos + 1) - 1
        text = text[:pos[0]] + text[pos[0] + 1:pos[1] + 1] + text[pos[1] + 2:]
        self._input_line.setText(text)
        self._input_line.setFocus()
        self._input_line.setSelection(pos[0], pos[1] - pos[0])

    def _show_error(self, message, category, filename, lineno,
            file=None, line=None):
        self._console.add_error(message[0])

    def execute_line(self):
        self.execute(str(self._input_line.text()))

    def execute(self, text):
        try:
            self._console.add_line(text)
            with catch_warning(OperationWarning, handle=self._show_error):
                perform_operation(text)
            self._input_line.setText('')
        except InvalidOperation, e:
            if e.fix is not None:
                self._input_line.setText(e.fix)
            if e.select is not None:
                self._input_line.setSelection(e.select[0],
                                              e.select[1] - e.select[0])
            self._console.add_error(e.message)
