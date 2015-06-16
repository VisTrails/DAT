from PyQt4 import QtCore, QtGui

from dat.gui.overlays import Overlay

from dat import MIMETYPE_DAT_VARIABLE
from dat.gui import translate
from dat.operations.typecasting import get_typecast_operations
from dat.vistrail_data import VistrailManager
from dat.vistrails_interface.wrappers import DataPort

from vistrails.core.vistrail.port_spec_item import PortSpecItem
from vistrails.gui.ports_pane import Parameter as GuiParameter


COMPATIBLE = 'yes'
TYPECASTABLE = 'cast'
INCOMPATIBLE = 'no'


stylesheet = """
DataParameter {
    background-color: #DDD;
    padding: 3px;
}

DataParameter[assigned="yes"] {
    border: 2px solid black;
}

DataParameter[assigned="yes"]:hover {
    background-color: #BBB;
}

DataParameter[assigned="no"] {
    border: 1px dotted black;
    font-style: oblique;
}

DataParameter[targeted="yes"][compatible="yes"] {
    background-color: rgb(187, 204, 255);
    border: 2px solid rgb(102, 153, 255);
    padding: 2px;
}

DataParameter[targeted="no"][compatible="yes"] {
    background-color: rgb(187, 204, 255);
}

DataParameter[targeted="yes"][compatible="cast"] {
    background-color: rgb(255, 238, 170);
    border: 2px solid rgb(255, 208, 0);
    padding: 2px;
}

DataParameter[targeted="no"][compatible="cast"] {
    background-color: rgb(255, 238, 170);
}

DataParameter[targeted="no"][compatible="no"] {
    background-color: rgb(255, 170, 170);
}

"""


class DataParameter(QtGui.QPushButton):
    def __init__(self, overlay, port_name, pos, variable, typecast=None,
                 append=False):
        QtGui.QPushButton.__init__(self)

        self.setSizePolicy(QtGui.QSizePolicy.Minimum,
                           QtGui.QSizePolicy.Fixed)
        self.setProperty('assigned', variable is not None and 'yes' or 'no')

        self._variable = variable
        if variable is not None:
            if typecast is not None:
                self.setText("(%s) %s" % (typecast, variable.name))
            else:
                self.setText(variable.name)

            self.connect(
                self,
                QtCore.SIGNAL('clicked()'),
                lambda: overlay.remove_parameter(port_name, pos))
        elif append:
            self.setText('+')
        else:
            _ = translate(DataParameter)
            self.setText(_("(not set)"))

    def update(self):
        if self._variable is not None:
            self.setText(self._variable.name)
        super(DataParameter, self).update()


class VariableDroppingOverlay(Overlay):
    """The main overlay.

    Displays targets for each parameter, according to the current plot, and
    type-checks them.
    """
    def __init__(self, cellcontainer, **kwargs):
        Overlay.__init__(self, cellcontainer, **kwargs)

        self.setStyleSheet(stylesheet)

        # Type-checking, so we can show which parameters are suitable to
        # receive the drop
        mimeData = kwargs.get('mimeData')
        if not mimeData or not mimeData.hasFormat(MIMETYPE_DAT_VARIABLE):
            self._compatible_ports = None
        else:
            varname = str(mimeData.data(MIMETYPE_DAT_VARIABLE))
            variable = (VistrailManager(self._cell._controller)
                        .get_variable(varname))
            self._compatible_ports = []
            for port in self._cell._plot.ports:
                if issubclass(variable.type.module, port.type.module):
                    self._compatible_ports.append(COMPATIBLE)
                else:
                    if get_typecast_operations(
                            variable.type,
                            port.type):
                        self._compatible_ports.append(TYPECASTABLE)
                    else:
                        self._compatible_ports.append(INCOMPATIBLE)

        self._cell._parameter_hovered = None

        self.setupUi(kwargs.get('overlayed', True))

    def setupUi(self, overlayed):
        _ = translate(VariableDroppingOverlay)

        main_layout = QtGui.QVBoxLayout()

        name_layout = QtGui.QHBoxLayout()
        name_label = QtGui.QLabel(self._cell._plot.name + " (")
        name_label.setObjectName('plot_name')
        name_layout.addWidget(name_label)
        name_layout.addStretch()
        if not overlayed:
            show_adv_config = QtGui.QPushButton("config")
            self.connect(show_adv_config, QtCore.SIGNAL('clicked()'),
                         self.show_advanced_config)
            name_layout.addWidget(show_adv_config)
        main_layout.addLayout(name_layout)

        spacing_layout = QtGui.QHBoxLayout()
        spacing_layout.addSpacing(20)
        ports_layout = QtGui.QFormLayout()
        ports_layout.setFieldGrowthPolicy(
            QtGui.QFormLayout.AllNonFixedFieldsGrow)

        self._parameters = []  # [[widget]]
        self._constant_widgets = dict()  # widget -> port
        self._unset_constant_labels = dict()  # widget -> QtGui.QLabel
        for i, port in enumerate(self._cell._plot.ports):
            widgets = []
            if isinstance(port, DataPort):
                param_panel = QtGui.QWidget()
                param_panel.setLayout(QtGui.QVBoxLayout())
                # Style changes according to the compatibility of the port with
                # the variable being dragged
                if self._compatible_ports is not None:
                    compatible = self._compatible_ports[i]
                else:
                    compatible = ''
                pos = 0
                for pos, variable in enumerate(
                        self._cell._parameters.get(port.name, [])):
                    param = DataParameter(self, port.name, pos,
                                          variable=variable.variable,
                                          typecast=variable.typecast)
                    param.setProperty('compatible', compatible)
                    param.setProperty('optional', port.optional)
                    param.setProperty('targeted', 'no')
                    widgets.append(param)
                    param_panel.layout().addWidget(param)
                if ((port.multiple_values and compatible == 'yes') or
                        not self._cell._parameters.get(port.name)):
                    param = DataParameter(self, port.name, pos,
                                          variable=None,
                                          append=compatible == 'yes')
                    param.setProperty('compatible', compatible)
                    param.setProperty('optional', port.optional)
                    param.setProperty('targeted', 'no')
                    widgets.append(param)
                    param_panel.layout().addWidget(param)
            else:  # isinstance(port, ConstantPort):
                gp = GuiParameter(port.type)
                gp.port_spec_item = PortSpecItem(id=-1, pos=0,
                                                 module=port.type.name,
                                                 package=port.type.package,
                                                 default=port.default_value,
                                                 entry_type=port.entry_type,
                                                 values=port.enum_values)
                try:
                    gp.strValue = self._cell._parameters[port.name][0].constant
                    isset = True
                except KeyError:
                    isset = False
                param = port.widget_class(gp)
                self._constant_widgets[param] = port.name
                param.contentsChanged.connect(self.constant_changed)
                param_panel = QtGui.QWidget()
                param_panel.setLayout(QtGui.QHBoxLayout())
                param_panel.layout().addWidget(param)
                if not isset:
                    label = QtGui.QLabel(_("(not set)"))
                    if not port.optional:
                        label.setStyleSheet('QLabel { color: red; }')
                    else:
                        label.setStyleSheet('QLabel { color: grey; }')
                    param_panel.layout().addWidget(label)
                    self._unset_constant_labels[param] = label
            label = QtGui.QLabel(port.name)
            label.setBuddy(param_panel)
            self._parameters.append(widgets)
            ports_layout.addRow(label, param_panel)

        # Closing parenthesis
        paren_label = QtGui.QLabel(")")
        paren_label.setObjectName('closing_paren')
        ports_layout.addRow(paren_label)
        spacing_layout.addLayout(ports_layout)

        main_layout.addLayout(spacing_layout)
        main_layout.addStretch(1)

        if (not overlayed and self._cell.widget() is not None and
                self._constant_widgets):
            self._execute_button = QtGui.QPushButton(_("Execute"))
            self.connect(self._execute_button, QtCore.SIGNAL('clicked()'),
                         lambda: self._cell._set_overlay(None))
            self._execute_button.setEnabled(False)
            self._cancel_button = QtGui.QPushButton(_("Cancel changes"))

            def cancel_pending():
                self._cell._cancel_pending()
                self._execute_button.setEnabled(False)
                self._cancel_button.setEnabled(False)

            self.connect(self._cancel_button, QtCore.SIGNAL('clicked()'),
                         cancel_pending)
            self._cancel_button.setEnabled(False)
            buttons = QtGui.QHBoxLayout()
            buttons.addStretch(1)
            buttons.addWidget(self._execute_button)
            buttons.addWidget(self._cancel_button)
            main_layout.addLayout(buttons)
        else:
            self._execute_button = None
            self._cancel_button = None

        self.setLayout(main_layout)

    def update(self):
        for panel in self._parameters:
            for child in panel:
                child.update()
        super(VariableDroppingOverlay, self).update()

    def set_mouse_position(self, x, y):
        # Find the currently targeted port: the compatible port closer to the
        # mouse

        if not self._compatible_ports:
            return  # Nothing to target

        targeted, mindist, pos = None, None, None
        for i, params in enumerate(self._parameters):
            for j, param in enumerate(params):
                if self._compatible_ports[i] != INCOMPATIBLE:
                    wy = param.pos().y() + param.parentWidget().pos().y()
                    wh = param.height()
                    if y < wy:
                        dist = wy - y
                    elif y > wy + wh:
                        dist = y - (wy + wh)
                    else:
                        targeted = i
                        pos = j
                        mindist = 0
                        break
                    if mindist is None or dist < mindist:
                        mindist = dist
                        targeted = i
                        pos = j
            if mindist == 0:
                break

        if (self._cell._parameter_hovered != targeted or
                self._cell._insert_pos != pos):
            def refresh(widget):
                style = self.style()
                style.unpolish(widget)
                style.polish(widget)
            if self._cell._parameter_hovered is not None:
                old = (self._parameters[self._cell._parameter_hovered]
                                       [self._cell._insert_pos])
                old.setProperty('targeted', 'no')
                refresh(old)

            if targeted is not None:
                new = self._parameters[targeted][pos]
                new.setProperty('targeted', 'yes')
                refresh(new)

            self._cell._parameter_hovered = targeted
            self._cell._insert_pos = pos

    def remove_parameter(self, port_name, pos):
        self._cell.remove_parameter(port_name, pos)

    def constant_changed(self, (widget, contents)):
        try:
            label = self._unset_constant_labels.pop(widget)
            label.setParent(None)
            label.deleteLater()
        except KeyError:
            pass
        changed = self._cell.change_constant(
            self._constant_widgets[widget],
            contents)
        if changed and self._execute_button is not None:
            self._execute_button.setEnabled(True)
            self._cancel_button.setEnabled(True)

    def show_advanced_config(self):
        # Get the pipeline info for the cell
        vistraildata = VistrailManager(self._cell._controller)
        pipeline = vistraildata.get_pipeline(self._cell.cellInfo)

        self._cell._set_overlay(pipeline.recipe.plot.configWidget)
        self._cell._overlay.setup(self._cell, pipeline.recipe.plot)
