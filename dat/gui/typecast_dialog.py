from PyQt4 import QtCore, QtGui

from dat.gui import translate
from dat.gui.generic import CategorizedListWidget
from dat.gui.operations import OperationItem

from vistrails.core.packagemanager import get_package_manager
from dat.vistrails_interface import CancelExecution


def choose_operation(typecasts, source_descriptor, expected_descriptor,
        parent=None):
    _ = translate('typecast_dialog')

    dialog = QtGui.QDialog(parent)
    dialog.setWindowTitle(_("Type casting"))
    layout = QtGui.QVBoxLayout()

    layout.addWidget(QtGui.QLabel(_(
            "A %s variable was put in a %s port. These are not compatible, "
            "but the following operations can do the conversion:")))
    list_widget = CategorizedListWidget()
    list_widget.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
    pm = get_package_manager()
    for operation in typecasts:
        package = pm.get_package_by_identifier(operation.package_identifier)
        item = OperationItem(operation, package.name)
        list_widget.addItem(item, item.category)
    layout.addWidget(list_widget)

    buttons = QtGui.QHBoxLayout()
    ok = QtGui.QPushButton(_("Typecast", "Accept typecast dialog button"))
    QtCore.QObject.connect(ok, QtCore.SIGNAL('clicked()'),
                           dialog, QtCore.SLOT('accept()'))
    buttons.addWidget(ok)
    cancel = QtGui.QPushButton(_("Cancel", "Reject typecast dialog button"))
    QtCore.QObject.connect(cancel, QtCore.SIGNAL('clicked()'),
                           dialog, QtCore.SLOT('reject()'))
    buttons.addWidget(cancel)
    layout.addLayout(buttons)

    dialog.setLayout(layout)
    if dialog.exec_() == QtGui.QDialog.Accepted:
        return list_widget.selectedItems()[0].operation
    else:
        raise CancelExecution
