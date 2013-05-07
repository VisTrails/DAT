from PyQt4 import QtCore, QtGui

from dat import MIMETYPE_DAT_VARIABLE
import dat.gui
from dat.gui import get_icon
from dat.gui.generic import DraggableListWidget, advanced_input_dialog
from dat.gui.load_variable_dialog import LoadVariableDialog, \
    VariableNameValidator
from dat.utils import bisect

from vistrails.core.application import get_vistrails_application


class VariablePanel(QtGui.QWidget):
    """The panel showing the DAT variables with some buttons.

    unregister_notifications() must be called if you intend this widget to be
    deleted, else it will still be referenced from the NotificationDispatcher.
    """
    variableSelected = QtCore.pyqtSignal('PyQt_PyObject')

    def __init__(self, vistraildata):
        QtGui.QWidget.__init__(self)

        self._vistraildata = vistraildata

        _ = dat.gui.translate(VariablePanel)

        layout = QtGui.QVBoxLayout()

        toolbar = QtGui.QToolBar()
        toolbar.setIconSize(QtCore.QSize(24,24))
        new_variable = QtGui.QAction(get_icon('new_variable.png'),
                                     _("New variable..."),
                                     self)
        toolbar.addAction(new_variable)
        delete_variable = QtGui.QAction(get_icon('delete_variable.png'),
                                        _("Delete variable"),
                                        self)
        toolbar.addAction(delete_variable)
        rename_variable = QtGui.QAction(get_icon('rename_variable.png'),
                                        _("Rename variable..."),
                                        self)
        toolbar.addAction(rename_variable)
        layout.addWidget(toolbar)

        self._list_widget = DraggableListWidget(self, MIMETYPE_DAT_VARIABLE)
        layout.addWidget(self._list_widget)

        self.setLayout(layout)

        # UI created; stop here if this panel is disabled
        if self._vistraildata is None:
            self.setEnabled(False)
            return

        self.connect(new_variable, QtCore.SIGNAL("triggered()"),
                     self.new_variable)
        self.connect(delete_variable, QtCore.SIGNAL("triggered()"),
                     self.delete_variable)
        self.connect(rename_variable, QtCore.SIGNAL("triggered()"),
                     self.rename_variable)

        def select_variable(varname):
            varname = str(varname)
            self.variableSelected.emit(vistraildata.get_variable(varname))
        self.connect(
                self._list_widget,
                QtCore.SIGNAL('currentTextChanged(QString)'),
                select_variable)

        self._variable_loader = LoadVariableDialog(
                self._vistraildata.controller,
                self)

        app = get_vistrails_application()
        app.register_notification('dat_new_variable', self.variable_added)
        app.register_notification('dat_removed_variable',
                                  self.variable_removed)

        for varname in self._vistraildata.variables:
            self.variable_added(self._vistraildata.controller, varname)

    def unregister_notifications(self):
        app = get_vistrails_application()
        app.unregister_notification('dat_new_variable', self.variable_added)
        app.unregister_notification('dat_removed_variable',
                                    self.variable_removed)

    def new_variable(self):
        """Called when a button is clicked.
        """
        self._variable_loader.load_variable()

    def delete_variable(self):
        """Called when a button is clicked.
        """
        _ = dat.gui.translate(VariablePanel)

        selected = self._list_widget.selectedItems()
        if not selected:
            return

        confirm = QtGui.QMessageBox.question(
                self,
                _("Are you sure?"),
                str(_("You are about to delete {num} variables. "
                      "Please confirm."))
                        .format(num=len(selected)),
                QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel,
                QtGui.QMessageBox.Cancel)
        if confirm == QtGui.QMessageBox.Ok:
            for item in selected:
                self._vistraildata.remove_variable(str(item.text()))

    def rename_variable(self):
        """Called when a button is clicked.
        """
        _ = dat.gui.translate(VariablePanel)

        selected = self._list_widget.selectedItems()
        if len(selected) > 1:
            self._list_widget.clearSelection()
            return
        elif not selected:
            return

        selected = selected[0]

        validator = VariableNameValidator(self._vistraildata)
        new_name, proceed = advanced_input_dialog(
                self,
                _("Rename variable", "Dialog title"),
                _("New name:"),
                selected.text(),
                default=selected.text(),
                validate=validator)

        if proceed and new_name:
            if not validator.unique(new_name):
                QtGui.QMessageBox.warning(
                        self, _("Couldn't rename variable"),
                        _("A variable '{name}' already exists!")
                                .format(name=new_name))
                return
            if not validator.format(new_name):
                QtGui.QMessageBox.warning(
                        self, _("Couldn't rename variable"),
                        _("The name you entered is not valid"))
                return
            varname = str(selected.text())
            self._vistraildata.rename_variable(varname, new_name)
            # This will trigger a variable_removed then a variable_added

    def variable_added(self, controller, varname, renamed_from=None):
        if controller != self._vistraildata.controller:
            return
        pos = bisect(
                self._list_widget.count(),
                lambda i: str(self._list_widget.item(i).text()),
                varname)
        self._list_widget.insertItem(pos, varname)

    def variable_removed(self, controller, varname, renamed_to=None):
        if controller != self._vistraildata.controller:
            return
        for i in xrange(self._list_widget.count()):
            if self._list_widget.item(i).text() == varname:
                self._list_widget.takeItem(i)
                break
