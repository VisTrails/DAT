from PyQt4 import QtCore, QtGui

from dat import MIMETYPE_DAT_VARIABLE
import dat.gui
from dat.gui import get_icon
from dat.gui.generic import DraggableListWidget
from dat.gui.load_variable_dialog import LoadVariableDialog
import dat.manager
from dat.utils import bisect

from vistrails.core.application import get_vistrails_application


class VariablePanel(QtGui.QWidget):
    def __init__(self):
        super(VariablePanel, self).__init__()

        _ = dat.gui.translate(VariablePanel)
        
        layout = QtGui.QVBoxLayout()

        toolbar = QtGui.QToolBar()
        toolbar.setIconSize(QtCore.QSize(24,24))
        new_variable = QtGui.QAction(get_icon('new_variable.png'),
                                     _("New variable..."),
                                     self)
        self.connect(new_variable, QtCore.SIGNAL("triggered()"),
                     self.new_variable)
        toolbar.addAction(new_variable)
        delete_variable = QtGui.QAction(get_icon('delete_variable.png'),
                                        _("Delete variable"),
                                        self)
        self.connect(delete_variable, QtCore.SIGNAL("triggered()"),
                     self.delete_variable)
        toolbar.addAction(delete_variable)
        rename_variable = QtGui.QAction(get_icon('rename_variable.png'),
                                        _("Rename variable..."),
                                        self)
        self.connect(rename_variable, QtCore.SIGNAL("triggered()"),
                     self.rename_variable)
        toolbar.addAction(rename_variable)
        layout.addWidget(toolbar)

        self._list_widget = DraggableListWidget(self, MIMETYPE_DAT_VARIABLE)
        layout.addWidget(self._list_widget)

        self.setLayout(layout)

        self._variable_loader = LoadVariableDialog(self)

        app = get_vistrails_application()
        app.register_notification('dat_new_variable', self.variable_added)
        app.register_notification('dat_removed_variable', self.variable_removed)

        for varname in dat.manager.Manager().variables:
            self.variable_added(varname)

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
            manager = dat.manager.Manager()
            for item in selected:
                manager.remove_variable(str(item.text()))

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

        new_name, proceed = QtGui.QInputDialog.getText(
                self,
                _("Rename variable", "Dialog title"),
                _("New name:"),
                QtGui.QLineEdit.Normal,
                selected.text())
        new_name = str(new_name)

        if proceed and new_name:
            if dat.manager.Manager().get_variable(new_name) is not None:
                QtGui.QMessageBox.warning(
                        self, _("Couldn't rename variable"),
                        _("A variable '{name}' already exists!")
                                .format(name=new_name))
                return
            varname = str(selected.text())
            dat.manager.Manager().rename_variable(varname, new_name)
                # This will trigger a variable_removed then a variable_added

    def variable_added(self, varname, renamed_from=None):
        pos = bisect(
                self._list_widget.count(),
                lambda i: str(self._list_widget.item(i).text()),
                varname)
        self._list_widget.insertItem(pos, varname)

    def variable_removed(self, varname, renamed_to=None):
        for i in xrange(self._list_widget.count()):
            if self._list_widget.item(i).text() == varname:
                self._list_widget.takeItem(i)
                break
