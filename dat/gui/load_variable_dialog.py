import re
from PyQt4 import QtCore, QtGui

from dat import DEFAULT_VARIABLE_NAME
from dat.gui import translate
from dat.gui.generic import AdvancedLineEdit
from dat.global_data import GlobalManager
from dat.vistrail_data import VistrailManager
from dat.vistrails_interface import FileVariableLoader, CustomVariableLoader

from vistrails.core.application import get_vistrails_application


_varname_format = re.compile('^(.+) \(([0-9]+)\)$')

def unique_varname(varname, mngr):
    """Make a variable name unique.

    Adds or increment a number suffix to a variable name to make it unique.

    >>> mngr = VistrailManager()
    >>> unique_varname('variable', mngr)
    'variable (2)'
    >>> unique_varname('variable (4)', mngr)
    'variable (5)'
    """
    match = _varname_format.match(varname)
    num = 1
    if match is not None:
        varname = match.group(1)
        num = int(match.group(2))
    while True:
        num += 1
        new_varname = '%s (%d)' % (varname, num)
        if mngr.get_variable(new_varname) is None:
            return new_varname


class FileLoaderPanel(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)

        _ = translate(LoadVariableDialog)

        self._file_loaders = set()

        main_layout = QtGui.QVBoxLayout()

        header_layout = QtGui.QFormLayout()
        file_edit = QtGui.QHBoxLayout()
        self._file_edit = QtGui.QLineEdit()
        self._file_edit.setEnabled(False)
        file_edit.addWidget(self._file_edit)
        file_button = QtGui.QPushButton(_("Browse..."))
        self.connect(file_button, QtCore.SIGNAL('clicked()'),
                     self.pick_file)
        file_edit.addWidget(file_button)
        header_layout.addRow(_("File:"), file_edit)
        self._loader_list = QtGui.QComboBox()
        self.connect(self._loader_list,
                     QtCore.SIGNAL('currentIndexChanged(int)'),
                     self.update_widget)
        header_layout.addRow(_("Loader:"), self._loader_list)
        main_layout.addLayout(header_layout)

        self._loader_stack = QtGui.QStackedWidget()
        loader_groupbox = QtGui.QGroupBox(_("Loader parameters"))
        groupbox_layout = QtGui.QVBoxLayout()
        groupbox_layout.addWidget(self._loader_stack)
        loader_groupbox.setLayout(groupbox_layout)
        main_layout.addWidget(loader_groupbox)

        self.setLayout(main_layout)

        self.select_file('')

    def pick_file(self):
        _ = translate(LoadVariableDialog)

        # Pick a file
        picked = QtGui.QFileDialog.getOpenFileName(
                self,
                _("Choose a file"))
        if picked.isNull():
            return

        self.select_file(str(picked))

    def select_file(self, filename):
        _ = translate(LoadVariableDialog)

        # Update self._file_edit
        self._file_edit.setText(filename)

        # Update self._loader_list
        self._loader_list.clear()
        while self._loader_stack.count() > 0:
            self._loader_stack.removeWidget(self._loader_stack.widget(0))
        if filename != '':
            for loader in self._file_loaders:
                if loader.can_load(filename):
                    widget = loader(filename)
                    widget.default_variable_name_observer = (
                            self.default_variable_name_changed)
                    # The order of these lines is important, because adding an
                    # item to the list emits a signal
                    self._loader_stack.addWidget(widget)
                    self._loader_list.addItem(loader.loader_tab_name, widget)
            if self._loader_stack.count() == 0:
                self._loader_stack.addWidget(
                        QtGui.QLabel(_("No loader accepts this file")))
        else:
            self._loader_stack.addWidget(QtGui.QLabel(_("No file selected")))

        # Update the widget stack
        self.update_widget()

    def update_widget(self, index=None):
        if index is None:
            index = self._loader_list.currentIndex()
        if index == -1:
            return
        self._loader_stack.setCurrentIndex(index)

        self.default_variable_name_observer(
                self,
                self._loader_stack.widget(index).get_default_variable_name())

    def add_file_loader(self, loader):
        if not loader in self._file_loaders:
            self._file_loaders.add(loader)

    def remove_file_loader(self, loader):
        if loader in self._file_loaders:
            self._file_loaders.remove(loader)

    def reset(self):
        self.select_file('')

    def default_variable_name_changed(self, loader, new_default_name):
        if self._loader_list.currentIndex() == -1:
            return None
        current_loader = self._loader_stack.currentWidget()
        if current_loader is loader:
            self.default_variable_name_observer(self, new_default_name)

    def get_default_variable_name(self):
        if self._loader_list.currentIndex() == -1:
            return DEFAULT_VARIABLE_NAME
        current_loader = self._loader_stack.currentWidget()
        name = current_loader.get_default_variable_name()
        return name

    def load(self):
        if self._loader_list.currentIndex() == -1:
            return None
        loader = self._loader_stack.currentWidget()
        return loader.load()


class LoadVariableDialog(QtGui.QDialog):
    def __init__(self, controller, parent=None):
        QtGui.QDialog.__init__(self, parent, QtCore.Qt.Dialog)

        self._vistraildata = VistrailManager(controller)

        _ = translate(LoadVariableDialog)

        self.setWindowTitle(_("Load variable"))

        self._tabs = []

        main_layout = QtGui.QVBoxLayout()

        self._tab_widget = QtGui.QTabWidget()
        self.connect(self._tab_widget, QtCore.SIGNAL('currentChanged(int)'),
                     self.update_varname)
        main_layout.addWidget(self._tab_widget)

        varname_layout = QtGui.QHBoxLayout()
        varname_layout.addWidget(QtGui.QLabel(_("Variable name:")))
        self._varname_edit = AdvancedLineEdit(
                "variable",
                default="variable",
                validate=self._validate_varname,
                flags=(AdvancedLineEdit.COLOR_VALIDITY |
                       AdvancedLineEdit.COLOR_DEFAULTVALUE |
                       AdvancedLineEdit.FOLLOW_DEFAULT_UPDATE))
        varname_layout.addWidget(self._varname_edit)
        main_layout.addLayout(varname_layout)

        buttons_layout = QtGui.QHBoxLayout()
        load_cont_button = QtGui.QPushButton(_("Load and close"))
        self.connect(load_cont_button, QtCore.SIGNAL('clicked()'),
                     self.loadclose_clicked)
        buttons_layout.addWidget(load_cont_button)
        load_button = QtGui.QPushButton(_("Load"))
        self.connect(load_button, QtCore.SIGNAL('clicked()'),
                     self.load_clicked)
        buttons_layout.addWidget(load_button)
        cancel_button = QtGui.QPushButton(_("Cancel"))
        self.connect(cancel_button, QtCore.SIGNAL('clicked()'), self.cancel)
        buttons_layout.addWidget(cancel_button)
        main_layout.addLayout(buttons_layout)

        self.setLayout(main_layout)

        self._file_loader = FileLoaderPanel()
        self._file_loader.default_variable_name_observer = (
                self.default_variable_name_changed)
        self._add_tab(self._file_loader, _("File"))

        app = get_vistrails_application()
        app.register_notification('dat_new_loader', self.loader_added)
        app.register_notification('dat_removed_loader', self.loader_removed)
        for loader in GlobalManager.variable_loaders:
            self.loader_added(loader)

        idx = self._tab_widget.currentIndex()
        if idx >= 0:
            loader = self._tabs[idx]
            self._varname_edit.setDefault(loader.get_default_variable_name())
        else:
            self._varname_edit.setDefault(DEFAULT_VARIABLE_NAME)
        self._varname_edit.reset()

    def update_varname(self, idx):
        if idx >= 0:
            loader = self._tabs[idx]
            self.default_variable_name_changed(
                    None, loader.get_default_variable_name())

    def _add_tab(self, tab, name):
        widget = QtGui.QWidget()
        lay = QtGui.QVBoxLayout()
        lay.addWidget(tab)
        lay.addStretch()
        widget.setLayout(lay)

        # The order of these lines is important, because adding a tab emits a
        # signal
        self._tabs.append(tab)
        self._tab_widget.addTab(widget, name)

    def _remove_tabs(self, tabfilter):
        idx = 0
        while idx < len(self._tabs):
            if tabfilter(self._tabs[idx]):
                del self._tabs[idx]
                self._tab_widget.removeTab(idx)
            else:
                idx += 1

    def loader_added(self, loader):
        if issubclass(loader, FileVariableLoader):
            self._file_loader.add_file_loader(loader)
        elif issubclass(loader, CustomVariableLoader):
            l = loader()
            l.default_variable_name_observer = (
                    self.default_variable_name_changed)
            self._add_tab(l, loader.loader_tab_name)

    def loader_removed(self, loader):
        if issubclass(loader, FileVariableLoader):
            self._file_loader.remove_file_loader(loader)
        elif issubclass(loader, CustomVariableLoader):
            self._remove_tabs(lambda tab: isinstance(tab, loader))

    def default_variable_name_changed(self, loader, new_default_name):
        idx = self._tab_widget.currentIndex()
        if idx == -1:
            return
        current_loader = self._tabs[idx]
        if not (loader is None or loader is current_loader):
            return

        self._default_varname = new_default_name
        self._varname_edit.setDefault(self._default_varname)

    def load_variable(self):
        if not self.isVisible():
            self.setVisible(True)
            for tab in self._tabs:
                tab.reset()

    def cancel(self):
        self.setVisible(False)

    def loadclose_clicked(self):
        if self.load_clicked():
            self.setVisible(False)

    def load_clicked(self):
        varname = self._varname_edit.text()
        if varname.isNull() or varname.isEmpty():
            self._varname_edit.setFocus()
            return False
        varname = str(varname)
        if self._vistraildata.get_variable(varname) is not None:
            varname = unique_varname(varname, self._vistraildata)
            self._varname_edit.setText(varname)
            self._varname_edit.setFocus()
            return False
        loader = self._tabs[self._tab_widget.currentIndex()]
        variable = loader.load()
        if variable is None:
            # Here we assume the loader displayed the error itself in some way
            return False
        self._vistraildata.new_variable(varname, variable)
        self._varname_edit.setDefault(self._default_varname)
        return True

    def _validate_varname(self, varname):
        if varname.isNull() or varname.isEmpty():
            return False
        varname = str(varname)
        if self._vistraildata.get_variable(varname) is not None:
            return False
        return True
