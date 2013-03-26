from PyQt4 import QtCore, QtGui

from dat import PipelineInformation
from dat.gui.overlays import Overlay
from dat.vistrail_data import VistrailManager
from dat.vistrails_interface import get_plot_modules

from vistrails.core.modules.module_registry import get_module_registry, \
    ModuleRegistryException
from vistrails.gui.ports_pane import PortsList, PortItem


class PlotConfigOverlay(Overlay):
    """Base class for high level plot editors

    Must implement setup(self, cell, plot), which is called
    when the widget is shown.
    """

    def setup(self, cell, plot):
        raise NotImplementedError


class DefaultPlotConfigOverlay(PlotConfigOverlay):
    """Default widget for editing 'advanced' plot settings.

    Shows PortList widget for each module in plot. If the module has an
    advanced editor, that is shown instead.
    """
    def __init__(self, cellcontainer):
        Overlay.__init__(self, cellcontainer, False)

        self.setSizePolicy(QtGui.QSizePolicy.Ignored,
                           QtGui.QSizePolicy.Ignored)

        # Create tab widget
        self.tabWidget = QtGui.QTabWidget()

        # Create buttons
        btnApply = QtGui.QPushButton("&Apply")
        btnOk = QtGui.QPushButton("O&k")
        btnReset = QtGui.QPushButton("&Reset")

        # Connect buttons
        btnApply.clicked.connect(self.applyClicked)
        btnOk.clicked.connect(self.okClicked)
        btnReset.clicked.connect(self.resetClicked)

        # Add buttons to layout
        layoutButtons = QtGui.QHBoxLayout()
        layoutButtons.addWidget(btnReset)
        layoutButtons.addStretch()
        layoutButtons.addWidget(btnApply)
        layoutButtons.addWidget(btnOk)

        # Add tabwidget above buttons
        vLayout = QtGui.QVBoxLayout()
        vLayout.addWidget(self.tabWidget)
        vLayout.addLayout(layoutButtons)

        self.setLayout(vLayout)

        self.cell = None
        self.plot = None

    def setup(self, cell, plot):
        self.cell = cell
        self.plot = plot

        # Get pipeline of the cell
        mngr = VistrailManager(cell._controller)
        pipelineInfo = mngr.get_pipeline(cell.cellInfo)

        # Clear old tabs
        self.tabWidget.clear()

        # Get all of the plot modules in the pipeline
        plot_modules = get_plot_modules(
                pipelineInfo,
                cell._controller.current_pipeline)

        registry = get_module_registry()
        getter = registry.get_configuration_widget
        for module in plot_modules:
            widgetType = None
            widget = None

            # Try to get custom config widget for the module
            try:
                widgetType = \
                    getter(module.package, module.name, module.namespace)
            except ModuleRegistryException:
                pass

            if widgetType:
                # Use custom widget
                widget = widgetType(module, cell._controller)
                self.connect(widget, QtCore.SIGNAL("doneConfigure"),
                             self.configureDone)
                self.connect(widget, QtCore.SIGNAL("stateChanged"),
                             self.stateChanged)
            else:
                # Use PortsList widget, only if module has ports
                widget = DATPortsList(self)
                widget.update_module(module)
                if len(widget.port_spec_items) > 0:
                    widget.set_controller(cell._controller)
                else:
                    widget = None

            # Add widget in new tab
            if widget:
                self.tabWidget.addTab(widget, module.name)

    def stateChanged(self):
        pass

    def configureDone(self):
        pass

    def applyClicked(self):
        self.okClicked()

        # Bring this overlay back up
        self.cell._set_overlay(DefaultPlotConfigOverlay)
        mngr = VistrailManager(self.cell._controller)
        pipeline = mngr.get_pipeline(self.cell.cellInfo)
        self.cell._overlay.setup(self.cell, pipeline.recipe.plot)

    def okClicked(self):
        mngr = VistrailManager(self.cell._controller)
        pipeline = mngr.get_pipeline(self.cell.cellInfo)
        if pipeline.version != self.cell._controller.current_version:
            new_pipeline = PipelineInformation(
                    self.cell._controller.current_version,
                    pipeline.recipe,
                    pipeline.conn_map,
                    pipeline.port_map)
            mngr.created_pipeline(self.cell.cellInfo, new_pipeline)
            self.cell.update_pipeline()
        else:
            self.cell._set_overlay(None)

    def resetClicked(self):
        mngr = VistrailManager(self.cell._controller)
        pipeline = mngr.get_pipeline(self.cell.cellInfo)
        if pipeline.version != self.cell._controller.current_version:
            self.cell._controller.change_selected_version(pipeline.version)
            currentTabIndex = self.tabWidget.currentIndex()
            self.setup(self.cell, self.plot)
            self.tabWidget.setCurrentIndex(currentTabIndex)


class DATPortItem(PortItem):

    def build_item(self, port_spec, is_connected, is_optional, is_visible):
        PortItem.build_item(self, port_spec, is_connected,
                            is_optional, is_visible)
        self.setIcon(0, PortItem.null_icon)
        self.setIcon(1, PortItem.null_icon)


class DATPortsList(PortsList):
    """ Only input ports of constant type that aren't connected show up.
    Visibility and linked columns are removed
    """
    def __init__(self, parent=None):
        PortsList.__init__(self, "input", parent)

    def include_port(self, port_spec):
        """Determines whether or not a port should show up in this list.
        """
        connected = port_spec.name in self.module.connected_input_ports
        constant = get_module_registry().is_method(port_spec)
        return not connected and constant

    def create_port_item(self, port_spec, is_connected, is_optional,
                 is_visible, parent=None):
        """Creates the port item
        """
        return PortItem(port_spec, is_connected, True, False, parent)

    # Override visible_clicked to prevent changing this
    def visible_clicked(self, item):
        pass
