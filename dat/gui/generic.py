from PyQt4 import QtCore, QtGui

from dat.gui import dragging_to_overlays, get_icon, translate
from dat.utils import bisect


class DraggableListWidget(QtGui.QListWidget):
    """A QListWidget whose items can be dragged.

    The mimetype of the items can be passed to the constructor.
    The actual data of each element can be customized by overriding the
    buildData() method, that takes the item and returns a QMimeData object.

    By default, the mimetype is 'text/plain' and the data is simply the caption
    of the item.
    """
    def __init__(self, parent=None, mimetype='text/plain'):
        """Constructor.

        mimetype is the mimetype of the elements of the list.
        """
        QtGui.QListWidget.__init__(self, parent)
        self._mime_type = mimetype
        self.setDragEnabled(True)
        self.setDragDropMode(QtGui.QAbstractItemView.DragOnly)

    def buildData(self, item):
        """Builds the data for a draggable item.
        """
        data = QtCore.QMimeData()
        data.setData(self._mime_type, item.text().toAscii())
        return data

    def startDrag(self, actions):
        indexes = self.selectedIndexes()
        if len(indexes) == 1:
            data = self.buildData(self.itemFromIndex(indexes[0]))

            drag = QtGui.QDrag(self)
            drag.setMimeData(data)
            with dragging_to_overlays():
                drag.start(QtCore.Qt.CopyAction)


class CategorizedListWidget(QtGui.QTreeWidget):
    def __init__(self, parent=None, columns=1):
        QtGui.QTreeWidget.__init__(self, parent)
        self.setColumnCount(columns)
        self.setHeaderHidden(True)
        self._categories = dict()
                # category: str -> (
                #     top_level_widget: QTreeWidgetItem,
                #     {text: str OR item -> item: QTreeWidgetItem})

    def addItem(self, item, category):
        if isinstance(item, (str, unicode)):
            w = QtGui.QTreeWidgetItem([item])
        elif isinstance(item, QtGui.QTreeWidgetItem):
            w = item
        else:
            raise TypeError
        try:
            top_level, items = self._categories[category]
        except KeyError:
            top_level = QtGui.QTreeWidgetItem([category])
            pos = bisect(
                    self.topLevelItemCount(),
                    lambda i: str(self.topLevelItem(i).text(0)),
                    category,
                    comp=lambda x, y: x.lower() < y.lower())
            self.insertTopLevelItem(pos, top_level)
            self._categories[category] = top_level, {item: w}
        else:
            items[item] = w
        top_level.addChild(w)

    def removeItem(self, item, category):
        top_level, items = self._categories[category]
        if isinstance(item, (str, unicode)):
            w = items.pop(item)
        elif isinstance(item, QtGui.QTreeWidgetItem):
            w = items.pop(item) # w == item
        else:
            raise TypeError
        top_level.removeChild(w)
        if not items:
            del self._categories[category]
            for i in xrange(self.topLevelItemCount()):
                if self.topLevelItem(i) is top_level:
                    self.takeTopLevelItem(i)
                    break


class DraggableCategorizedListWidget(CategorizedListWidget):
    def __init__(self, parent=None, mimetype='text/plain'):
        CategorizedListWidget.__init__(self, parent)
        self._mime_type = mimetype
        self.setDragEnabled(True)
        self.setDragDropMode(QtGui.QAbstractItemView.DragOnly)

    def buildData(self, item):
        """Builds the data for a draggable item.
        """
        data = QtCore.QMimeData()
        data.setData(self._mime_type, item.text(0).toAscii())
        return data

    def startDrag(self, actions):
        items = self.selectedItems()
        if len(items) == 1:
            item = items[0]
            try:
                if self._categories[str(item.text(0))][0] == item:
                    return
            except KeyError:
                pass

            data = self.buildData(item)

            drag = QtGui.QDrag(self)
            drag.setMimeData(data)
            with dragging_to_overlays():
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
        """Constructor.

        contents: initial contents of the widget.
        parent: parent widget or None, passed to QWidget's constructor.
        default: the default value of this widget or None.
        validate: a method that will be used to validate this widget's content,
        or None.
        flags: a combination of the following bits:
            COLOR_DISABLE: no coloring for the widget
            COLOR_VALIDITY: colors the widget differently whether its value is
            valid or not
            COLOR_DEFAULTVALUE: colors the widget differently when its value is
            the default
            FOLLOW_DEFAULT_UPDATE: if the default value is changed while it is
            also the current value, changes the current value as well

        If COLOR_VALIDITY and COLOR_DEFAULTVALUE are both set (the default),
        the widget will use the first relevant color in the order: invalid,
        default, valid. This means that the fact it is the default will not be
        shown if it's also invalid, and the fact it's valid will not be shown
        if the value if the default.
        """
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
        """Returns True if the current value is the default.

        Don't call this if no default was set.
        """
        return self._is_default

    def isValid(self):
        """Returns True if the current value passed validation.

        Don't call this if no validation function was set.
        """
        return self._prev_validation

    def setDefault(self, default):
        """Change the default value.

        IF FOLLOW_DEFAULTVALUE is set and the current value is the default,
        this will also change the current value.
        """
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
        """Reset the value to the default.

        Don't call this if no default was set.
        """
        self.setText(self._default)

    def resizeEvent(self, event):
        super(AdvancedLineEdit, self).resizeEvent(event)

        if self._default is not None:
            y = (self.height() - 16)//2
            x = self.width() - 16 - y

            self._reset_button.setGeometry(x, y, 16, 16)


def advanced_input_dialog(parent, title, label, init_text,
        default=None, validate=None, flags=AdvancedLineEdit.DEFAULTS):
    """Similar to QInputDialog#getText() but uses an AdvancedLineEdit.

    parent: parent widget or None, passed to QWidget's constructor.
    title: the string displayed in the title bar of the dialog
    label: the string displayed inside the dialog.
    init_text: initial value of the field.
    default: default value of the field, or None.
    validate: validation function for the field, or None.
    flags: flags passed to AdvancedLineEdit.

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


class ConsoleWidget(QtGui.QTextEdit):
    def __init__(self, parent=None):
        QtGui.QTextEdit.__init__(self, parent)
        self.setReadOnly(True)
        self.setFont(QtGui.QFont('Courier'))

    def add_line(self, text):
        self.append("%s<br/>" % text)

    def add_error(self, text):
        self.append("<span style=\"color: red\">%s</span><br/>" % text)


class SingleLineTextEdit(QtGui.QTextEdit):
    def __init__(self):
        QtGui.QTextEdit.__init__(self)
        self.document().setMaximumBlockCount(1)
        self.setAcceptRichText(False)
        self.setLineWrapMode(QtGui.QTextEdit.NoWrap)
        self.setMaximumHeight(self.document().size().height())
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

    def keyPressEvent(self, event):
        if event.key() in (QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return):
            self.emit(self.returnPressed)
            event.accept()
        else:
            QtGui.QTextEdit.keyPressEvent(self, event)

    def text(self):
        return self.toPlainText()

    def setText(self, text):
        self.setPlainText(text)

    def setSelection(self, start, length=0):
        cursor = self.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(start+length, QtGui.QTextCursor.KeepAnchor)
        self.setTextCursor(cursor)

    returnPressed = QtCore.SIGNAL('returnPressed()')


class ZoomPanGraphicsView(QtGui.QGraphicsView):
    _NOT_DRAGGING = 0
    _PANNING = 1
    _ZOOMING = 2

    itemClicked = QtCore.pyqtSignal('QGraphicsItem*')

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._dragging = ZoomPanGraphicsView._PANNING
            self.setCursor(QtCore.Qt.ClosedHandCursor)
        elif event.button() == QtCore.Qt.RightButton:
            self._dragging = ZoomPanGraphicsView._ZOOMING
            self.setCursor(QtCore.Qt.SizeVerCursor)
        else:
            event.ignore()
            return
        self._start_x = self._cur_x = event.x()
        self._start_y = self._cur_y = event.y()
        event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging == ZoomPanGraphicsView._PANNING:
            hs = self.horizontalScrollBar()
            hs.setValue(hs.value() - (event.x() - self._cur_x))
            vs = self.verticalScrollBar()
            vs.setValue(vs.value() - (event.y() - self._cur_y))
            self._cur_x = event.x()
            self._cur_y = event.y()
            event.accept()
        elif self._dragging == ZoomPanGraphicsView._ZOOMING:
            factor = pow(1.01, self._cur_y - event.y())
            self.scale(factor, factor)
            self._cur_y = event.y()
            event.accept()
        else:
            event.ignore()

    def mouseReleaseEvent(self, event):
        if self._dragging != ZoomPanGraphicsView._NOT_DRAGGING:
            self._dragging = ZoomPanGraphicsView._NOT_DRAGGING
            self.setCursor(QtCore.Qt.ArrowCursor)
            event.accept()
        else:
            event.ignore()
        mlen = abs(event.x() - self._start_x) + abs(event.y() - self._start_y)
        if event.button() == QtCore.Qt.LeftButton and mlen < 5:
            # Click
            self.itemClicked.emit(self.itemAt(event.pos()))
            event.accept()
