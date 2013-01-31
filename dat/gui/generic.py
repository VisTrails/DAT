from PyQt4 import QtCore, QtGui

from dat.gui import get_icon, translate


class DraggableListWidget(QtGui.QListWidget):
    def __init__(self, parent=None, mimetype='text/plain'):
        QtGui.QListWidget.__init__(self, parent)
        self._mime_type = mimetype
        self.setDragEnabled(True)
        self.setDragDropMode(QtGui.QAbstractItemView.DragOnly)

    def buildData(self, element):
        data = QtCore.QMimeData()
        data.setData(self._mime_type,
                     element.text().toAscii())
        return data

    def startDrag(self, actions):
        indexes = self.selectedIndexes()
        if len(indexes) == 1:
            data = self.buildData(self.itemFromIndex(indexes[0]))

            drag = QtGui.QDrag(self)
            drag.setMimeData(data)
            drag.start(QtCore.Qt.CopyAction)


class AdvancedLineEdit(QtGui.QLineEdit):
    """A modified QLineEdit that can be validated and reset.

    A validating function can be provided, it will be used to check the
    contents and color the widget's background accordingly.
    The function will receive a single parameter: the new text.

    A reset button can be shown that will set the widget's content to the
    default value.
    """
    COLOR_DISABLE = 0
    COLOR_VALIDITY = 1
    COLOR_DEFAULTVALUE = 2

    FOLLOW_DEFAULT_UPDATE = 4

    DEFAULTS = COLOR_VALIDITY | COLOR_DEFAULTVALUE

    def __init__(self, contents="", parent=None, default=None, validate=None,
            flags=DEFAULTS):
        QtGui.QLineEdit.__init__(self, contents, parent)

        self._flags = flags
        self._default = default
        self._validate = validate

        if self._default is not None:
            self._reset_button = QtGui.QPushButton(self)
            self._reset_button.setIcon(get_icon('reset.png'))
            self.connect(self._reset_button, QtCore.SIGNAL('clicked()'),
                         self.reset)

            self._is_default = self._default == contents
        else:
            self._reset_button = None

        if self._validate is not None:
            self._prev_validation = None
            self._text_changed(QtCore.QString(contents))

        self.connect(self, QtCore.SIGNAL('textChanged(QString)'),
                     self._text_changed)

    def _text_changed(self, text):
        changed = False
        if self._validate is not None:
            val = self._validate(str(text))
            if val is not self._prev_validation:
                self._prev_validation = val
                changed = True
        if self._default is not None:
            is_default = text == self._default
            if self._is_default != is_default:
                self._is_default = is_default
                changed = True

        if changed:
            self.setStyleSheet('QLineEdit{background: %s;}' % (
                               self._choose_color()))

    def _choose_color(self):
        if (self._validate is not None and
                self._flags & AdvancedLineEdit.COLOR_VALIDITY and
                not self._prev_validation):
            return "#DDAAAA" # invalid value
        elif (self._default is not None and
                self._flags & AdvancedLineEdit.COLOR_DEFAULTVALUE and
                self._is_default):
            return "#AAAADD" # default value
        elif (self._validate is not None and
                self._flags & AdvancedLineEdit.COLOR_VALIDITY and
                self._prev_validation):
            return "#AADDAA" # valid value
        else:
            return "#FFFFFF" # default

    def isDefault(self):
        return self._is_default

    def isValid(self):
        return self._prev_validation

    def setDefault(self, default):
        self._default = default
        if (self._flags & AdvancedLineEdit.FOLLOW_DEFAULT_UPDATE and
                self._is_default):
            if default != self.text():
                self.setText(default)
            else:
                self._text_changed(QtCore.QString(default))
        else:
            self._text_changed(self.text())

    def reset(self):
        self.setText(self._default)

    def resizeEvent(self, event):
        super(AdvancedLineEdit, self).resizeEvent(event)

        if self._default is not None:
            y = (self.height() - 16)/2
            x = self.width() - 16 - y

            self._reset_button.setGeometry(x, y, 16, 16)


def advanced_input_dialog(parent, title, label, init_text,
        default=None, validate=None, flags=AdvancedLineEdit.DEFAULTS):
    """ advanced_input_dialog(parent: QWidget, title: str, label: str,
            init_text: str, default: str, validate: function)
        -> result: str, success: bool

    Function similar to QInputDialog#getText() but uses an AdvancedLineEdit.

    Returns either (result: str, True) or (None, False).
    """
    _ = translate('advanced_input_dialog')

    dialog = QtGui.QDialog(parent)
    dialog.setWindowTitle(title)
    layout = QtGui.QVBoxLayout()

    layout.addWidget(QtGui.QLabel(label))
    lineedit = AdvancedLineEdit(init_text, None, default, validate, flags)
    layout.addWidget(lineedit)

    buttons = QtGui.QHBoxLayout()
    ok = QtGui.QPushButton(_("Ok", "Accept dialog button"))
    ok.setDefault(True)
    QtCore.QObject.connect(ok, QtCore.SIGNAL('clicked()'),
                           dialog, QtCore.SLOT('accept()'))
    buttons.addWidget(ok)
    cancel = QtGui.QPushButton(_("Cancel", "Reject dialog button"))
    QtCore.QObject.connect(cancel, QtCore.SIGNAL('clicked()'),
                           dialog, QtCore.SLOT('reject()'))
    buttons.addWidget(cancel)
    layout.addLayout(buttons)

    dialog.setLayout(layout)
    if dialog.exec_() == QtGui.QDialog.Accepted:
        return str(lineedit.text()), True
    else:
        return None, False
