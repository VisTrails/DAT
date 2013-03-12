from PyQt4 import QtCore, QtGui

from dat.gui.overlays import Overlay

from dat import MIMETYPE_DAT_VARIABLE
from dat.vistrail_data import VistrailManager
from dat.vistrails_interface import DataPort

from vistrails.gui.ports_pane import Parameter as GuiParameter


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

DataParameter[targeted="yes"] {
    background-color: rgb(187, 204, 255);
    border: 2px solid rgb(102, 153, 255);
    padding: 2px;
}

DataParameter[targeted="no"][compatible="yes"] {
    background-color: rgb(187, 204, 255);
}

DataParameter[targeted="no"][compatible="no"] {
    background-color: rgb(255, 170, 170);
}

"""


class DataParameter(QtGui.QPushButton):
    def __init__(self, overlay, port_name, variable):
        QtGui.QPushButton.__init__(self)

        self.setSizePolicy(QtGui.QSizePolicy.Minimum,
                           QtGui.QSizePolicy.Fixed)
        self.setProperty('assigned', variable is not None and 'yes' or 'no')

        self._variable = variable
        if variable is not None:
            self.setText(variable.name)

            self.connect(
                    self,
                    QtCore.SIGNAL('clicked()'),
                    lambda: overlay.remove_parameter(port_name))

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
            self._compatible_ports = [
                    port is None or issubclass(variable.type.module,
                                               port.type.module)
                    for port in self._cell._plot.ports]

        self._cell._parameter_hovered = None

        self.setupUi()

    def setupUi(self):
        main_layout = QtGui.QVBoxLayout()

        name_label = QtGui.QLabel(self._cell._plot.name + " (")
        name_label.setObjectName('plot_name')
        main_layout.addWidget(name_label)

        spacing_layout = QtGui.QHBoxLayout()
        spacing_layout.addSpacing(20)
        ports_layout = QtGui.QGridLayout()

        self._parameters = []
        self._constant_widgets = dict() # widget -> port
        for i, port in enumerate(self._cell._plot.ports):
            if isinstance(port, DataPort):
                # Style changes according to the compatibility of the port with
                # the variable being dragged
                if self._compatible_ports:
                    if self._compatible_ports[i]:
                        compatible = 'yes'
                    else:
                        compatible = 'no'
                else:
                    compatible = ''
                variable = self._cell._variables.get(port.name)
                targeted = self._cell._parameter_hovered == i and 'yes' or 'no'
                param = DataParameter(self, port.name, variable)
                param.setProperty('compatible', compatible)
                param.setProperty('optional', port.optional)
                param.setProperty('targeted', targeted)
            else: # isinstance(port, InputPort):
                gp = GuiParameter(port.type)
                try:
                    gp.strValue = self._cell._constants[port.name]
                except KeyError:
                    pass
                param = port.widget_class(gp)
                self._constant_widgets[param] = port.name
                self.connect(param, QtCore.SIGNAL('contentsChanged'),
                             self.constant_changed)
            label = QtGui.QLabel(port.name)
            label.setObjectName('port_name')
            label.setProperty('compatible', compatible)
            label.setProperty('optional', port.optional)
            label.setProperty('targeted', targeted)
            label.setBuddy(param)
            self._parameters.append(param)
            label.setBuddy(param)
            ports_layout.addWidget(label, i, 0)
            ports_layout.addWidget(param, i, 1)

        # Closing parenthesis
        paren_label = QtGui.QLabel(")")
        paren_label.setObjectName('closing_paren')
        ports_layout.addWidget(paren_label, ports_layout.rowCount(), 0)
        spacing_layout.addLayout(ports_layout)

        main_layout.addLayout(spacing_layout)
        main_layout.addStretch(0)
        self.setLayout(main_layout)

    def update(self):
        for child in self._parameters:
            child.update()
        super(VariableDroppingOverlay, self).update()

    def set_mouse_position(self, x, y):
        # Find the currently targeted port: the compatible port closer to the
        # mouse

        if not self._compatible_ports:
            return # Nothing to target

        targeted, mindist = None, None
        for i, param in enumerate(self._parameters):
            if self._compatible_ports[i]:
                wy = param.pos().y()
                wh = param.height()
                if y < wy:
                    dist = wy - y
                elif y > wy + wh:
                    dist = y - (wy + wh)
                else:
                    targeted = i
                    break
                if mindist is None or dist < mindist:
                    mindist = dist
                    targeted = i

        if self._cell._parameter_hovered != targeted:
            def refresh(widget):
                style = self.style()
                style.unpolish(widget)
                style.polish(widget)
            if self._cell._parameter_hovered is not None:
                old = self._parameters[self._cell._parameter_hovered]
                old.setProperty('targeted', 'no')
                refresh(old)

            new = self._parameters[targeted]
            new.setProperty('targeted', 'yes')
            refresh(new)

            self._cell._parameter_hovered = targeted

    def remove_parameter(self, port_name):
        self._cell.remove_parameter(port_name)

    def constant_changed(self, args):
        widget, contents = args # params are packed as a tuple for some reason
        self._cell.change_constant(self._constant_widgets[widget], contents)

    def mouseReleaseEvent(self, event):
        metrics = self.fontMetrics()
        height = metrics.height()
        
        #show advanced plot config
        if event.y() > self._parameters[-1].height() + self._parameters[-1].y() + height*2:
            #get pipeline of the cell
            mngr = VistrailManager(self._cell._controller)
            pipeline = mngr.get_pipeline(self._cell.cellInfo)
            self._cell._set_overlay(pipeline.recipe.plot.configWidget)
            self._cell._overlay.setup(self._cell, pipeline.recipe.plot)
            return
        
        Overlay.mouseReleaseEvent(self, event)
