from PyQt4 import QtCore, QtGui

import dat.gui
from dat.gui import get_icon


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

        self._list_widget = QtGui.QListWidget()
        self._list_widget.addItem("Var1")
        self._list_widget.addItem("Var2")
        self._list_widget.addItem("Var3")
        layout.addWidget(self._list_widget)

        self.setLayout(layout)

    def new_variable(self):
        """Called when a button is clicked.
        """
        # TODO : display variable loader dialog

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
                # We're using Python, we can't just 'delete item;'
                self._list_widget.takeItem(
                        self._list_widget.indexFromItem(item))

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

        if proceed and new_name:
            selected.setText(new_name)
