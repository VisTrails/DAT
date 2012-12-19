from PyQt4 import QtCore, QtGui

import dat.gui
import dat.manager
from dat.packages import FileVariableLoader, CustomVariableLoader


class FileLoaderPanel(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)

        _ = dat.gui.translate(LoadVariableDialog)

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
        _ = dat.gui.translate(LoadVariableDialog)

        # Pick a file
        picked = QtGui.QFileDialog.getOpenFileName(
                self,
                _("Choose a file"))
        if picked.isNull():
            return

        self.select_file(str(picked))

    def select_file(self, filename):
        _ = dat.gui.translate(LoadVariableDialog)

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
                    self._loader_list.addItem(loader.loader_tab_name, widget)
                    self._loader_stack.addWidget(widget)
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

    def add_file_loader(self, loader):
        if not loader in self._file_loaders:
            self._file_loaders.add(loader)

    def remove_file_loader(self, loader):
        if loader in self._file_loaders:
            self._file_loaders.remove(loader)

    def reset(self):
        self.select_file('')

    def default_variable_name_changed(self, loader, new_default_name):
        # TODO : set variable name under condition
        pass


class LoadVariableDialog(QtGui.QDialog):
    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent, QtCore.Qt.Dialog)

        _ = dat.gui.translate(LoadVariableDialog)

        self.setWindowTitle(_("Load variable"))

        self._tabs = []

        main_layout = QtGui.QVBoxLayout()

        self._tab_widget = QtGui.QTabWidget()
        self._file_loader = FileLoaderPanel()
        self._add_tab(self._file_loader, _("File"))
        main_layout.addWidget(self._tab_widget)

        varname_layout = QtGui.QHBoxLayout()
        varname_layout.addWidget(QtGui.QLabel(_("Variable name:")))
        self._varname_edit = QtGui.QLineEdit()
        varname_layout.addWidget(self._varname_edit)
        main_layout.addLayout(varname_layout)

        buttons_layout = QtGui.QHBoxLayout()
        load_cont_button = QtGui.QPushButton(_("Load and continue"))
        self.connect(load_cont_button, QtCore.SIGNAL('clicked()'),
                     self.loadcont_clicked)
        buttons_layout.addWidget(load_cont_button)
        load_button = QtGui.QPushButton(_("Load"))
        self.connect(load_button, QtCore.SIGNAL('clicked()'), self.load_clicked)
        buttons_layout.addWidget(load_button)
        cancel_button = QtGui.QPushButton(_("Cancel"))
        self.connect(cancel_button, QtCore.SIGNAL('clicked()'), self.cancel)
        buttons_layout.addWidget(cancel_button)
        main_layout.addLayout(buttons_layout)

        self.setLayout(main_layout)

        dat.manager.Manager().add_loader_observer((self.loader_added,
                                                   self.loader_removed))
        for loader in dat.manager.Manager().variable_loaders:
            self.loader_added(loader)

    def _add_tab(self, tab, name):
        widget = QtGui.QWidget()
        lay = QtGui.QVBoxLayout()
        lay.addWidget(tab)
        lay.addStretch()
        widget.setLayout(lay)

        self._tab_widget.addTab(widget, name)
        self._tabs.append(tab)

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
        # TODO
        pass

    def load_variable(self):
        if not self.isVisible():
            self.setVisible(True)
            for tab in self._tabs:
                tab.reset()

    def cancel(self):
        self.setVisible(False)

    def loadcont_clicked(self):
        if self.load_clicked():
            self.setVisible(False)

    def load_clicked(self):
        # TODO : set variable name under condition
        return True
