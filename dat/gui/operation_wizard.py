from PyQt4 import QtCore, QtGui

from dat import DEFAULT_VARIABLE_NAME, MIMETYPE_DAT_VARIABLE
from dat.gui import translate
from dat.gui.generic import AdvancedLineEdit, DraggableListWidget
from dat.gui.load_variable_dialog import VariableNameValidator
from dat.utils import bisect
from dat.vistrail_data import VistrailManager
from dat.vistrails_interface import ArgumentWrapper, Variable


class OperationWizard(QtGui.QDialog):
    """Base class of the operation wizards.

    This class offers the basic behavior and functionalities needed by an
    operation wizard. It can be subclassed in VisTrails packages to add wizards
    to operations.

    A wizard is a dialog that is opened by clicking on the relevant icon to the
    right of an operation name. It then shows a graphical UI intended to do a
    variable operation graphically. When the user accepts, the wizard returns
    the new variable or operation string to DAT.
    """
    VAR_HIDE = 0
    VAR_SELECT = 1
    VAR_DRAG = 2

    def __init__(self, parent, variables=VAR_HIDE):
        """Setups the widget.

        If variables is not VAR_HIDE, a list of the variables will be displayed
        on the right. You can override variable_filter to choose which
        variables are to be displayed.

        If VAR_SELECT is used, variable_selected(variable) will be called when
        the selection changes.
        """
        _ = translate(OperationWizard)

        QtGui.QDialog.__init__(self, parent, QtCore.Qt.Dialog)

        self._vistraildata = VistrailManager()
        self._selected_varname = None

        self._has_error = False

        var_right_layout = QtGui.QHBoxLayout()
        vlayout = QtGui.QVBoxLayout()

        self._validator = VariableNameValidator(VistrailManager())

        varname_layout = QtGui.QHBoxLayout()
        varname_layout.addWidget(QtGui.QLabel(_("Variable name:")))
        self._varname_edit = AdvancedLineEdit(
                DEFAULT_VARIABLE_NAME,
                default=DEFAULT_VARIABLE_NAME,
                validate=self._validator,
                flags=(AdvancedLineEdit.COLOR_VALIDITY |
                       AdvancedLineEdit.COLOR_DEFAULTVALUE |
                       AdvancedLineEdit.FOLLOW_DEFAULT_UPDATE))
        varname_layout.addWidget(self._varname_edit)
        vlayout.addStretch()
        vlayout.addLayout(varname_layout)

        # Create this wizard's specific layout
        app_layout = self.create_ui()
        assert app_layout is not None
        vlayout.insertLayout(0, app_layout)

        var_right_layout.addLayout(vlayout)

        # Optionally, put a list of variables on the right
        if variables != self.VAR_HIDE:
            self._variable_list = DraggableListWidget(
                    mimetype=MIMETYPE_DAT_VARIABLE)
            self._variable_list.setSizePolicy(
                    QtGui.QSizePolicy.Minimum,
                    self._variable_list.sizePolicy().horizontalPolicy())
            for varname in self._vistraildata.variables:
                if not self.variable_filter(
                        self._vistraildata.get_variable(varname)):
                    continue
                pos = bisect(
                        self._variable_list.count(),
                        lambda i: str(self._variable_list.item(i).text()),
                        varname)
                self._variable_list.insertItem(pos, varname)
            var_right_layout.addWidget(self._variable_list)

            if variables == self.VAR_SELECT:
                self._variable_list.setDragEnabled(False)
                self._variable_list.setSelectionMode(
                        QtGui.QAbstractItemView.SingleSelection)
                self.connect(
                        self._variable_list,
                        QtCore.SIGNAL('itemSelectionChanged()'),
                        self._selection_changed)

        main_layout = QtGui.QVBoxLayout()
        main_layout.addLayout(var_right_layout)

        self._error_label = QtGui.QLabel()
        font = self._error_label.font()
        font.setBold(True)
        self._error_label.setFont(font)
        self._error_label.setStyleSheet('color: red;')
        main_layout.addWidget(self._error_label)

        buttons = QtGui.QDialogButtonBox(
                QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel,
                QtCore.Qt.Horizontal)
        self.connect(buttons, QtCore.SIGNAL('accepted()'),
                     self._accept)
        self.connect(buttons, QtCore.SIGNAL('rejected()'),
                     self, QtCore.SLOT('reject()'))
        main_layout.addWidget(buttons)

        self.setLayout(main_layout)

    def _selection_changed(self):
        items = self._variable_list.selectedItems()
        if len(items) == 1:
            item = items[0]
            sel = str(item.text())
            if sel != self._selected_varname:
                self._selected_varname = sel
                self.variable_selected(self._vistraildata.get_variable(sel))

    def _accept(self):
        if self._has_error:
            return
        if not self._varname_edit.isValid():
            self._varname_edit.setFocus(QtCore.Qt.OtherFocusReason)
            return
        varname = str(self._varname_edit.text())
        result = self.make_operation(varname)
        if isinstance(result, Variable):
            # Operation was performed by make_operation()
            self._vistraildata.new_variable(varname, result)
            self.command = None
            self.accept()
        elif result is False:
            # Don't dismiss the dialog
            pass
        elif isinstance(result, basestring):
            # make_operation() gave us an expression to execute
            if '=' in result:
                self.command = result
            else:
                self.command = '%s = %s' % (varname, result)
            self.accept()
        elif (isinstance(result, tuple) and len(result) == 2 and
                isinstance(result[0], basestring) and
                isinstance(result[1], dict)):
            subworkflow, args = result
            # TODO : Use args from dictionary + 'variable'
            # self.get_variable_argument() to make the result
            raise NotImplementedError("Building the operation result from a "
                                      "subworkflow is not yet implemented")
        else:
            raise TypeError("make_operation returned an unexpected type")

    def get_variable_argument(self):
        variable_info = self._vistraildata.get_variable(self._selected_varname)
        variable = Variable.from_workflow(variable_info,
                                          record_materialized=False)
        return ArgumentWrapper(variable)

    def set_error(self, err):
        if err is None:
            self._error_label.hide()
            self._has_error = False
        else:
            if isinstance(err, BaseException):
                err = "%s: %s" % (err.__class__.__name__, err.message)
            self._error_label.setText(err)
            self._error_label.show()
            self._has_error = True

    def variable_filter(self, variable):
        return True

    def variable_selected(self, varname):
        pass

    def make_operation(self, target_var_name):
        raise NotImplementedError
