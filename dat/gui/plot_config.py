from PyQt4 import QtCore, QtGui

from dat import PipelineInformation
from dat.vistrail_data import VistrailManager

from vistrails.core.modules.module_registry import get_module_registry, \
    ModuleRegistryException
from vistrails.gui.ports_pane import PortsList, PortItem


class PlotConfigBase(QtGui.QWidget):
    """Base class for high level plot editors

    Must implement setup(self, cell, plot), which is called
    when the widget is shown.
    """

    def setup(self, cell, plot):
        raise NotImplementedError

class DefaultPlotConfig(PlotConfigBase):
    """Default widget for editing 'advanced' plot settings.

    Shows PortList widget for each module in plot. If the module has an
    advanced editor, that is shown instead.
    """
    def __init__(self, parent=None):
        PlotConfigBase.__init__(self, parent)

        self.setSizePolicy(QtGui.QSizePolicy.Ignored,
                           QtGui.QSizePolicy.Ignored)

        # Create tree widget
        self.treeWidget = QtGui.QTreeWidget()
        self.treeWidget.itemSelectionChanged.connect(self.itemSelectionChanged)
        
        # Create horizontal layout for tree and module widget
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.addWidget(self.treeWidget)

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
        layoutButtons.addWidget(btnApply)
        layoutButtons.addStretch()
        layoutButtons.addWidget(btnOk)

        # Add tree/module widgets above buttons
        vLayout = QtGui.QVBoxLayout()
        vLayout.addLayout(self.horizontalLayout)
        vLayout.addLayout(layoutButtons)

        self.setLayout(vLayout)

        self.cell = None
        self.plot = None
        self.module_widget = None
        self.item_module_map = dict()

    def setup(self, cell, plot):
        
        self.cell = cell
        self.plot = plot

        # Get pipeline of the cell
        mngr = VistrailManager(cell._controller)
        pipelineInfo = mngr.get_pipeline(cell.cellInfo)
        pipeline = cell._controller.current_pipeline
        
        #setup the tree
        self.treeWidget.clear()
        
        #get input modules
        input_modules = set(pipeline.modules[mod_id]
                            for lp in pipelineInfo.port_map.itervalues()
                            for mod_id, _ in lp)
        
        connections_from = cell._controller.get_connections_from
        connections_to = cell._controller.get_connections_to

        def add_to_tree(module, parent=None):
            
            item = QtGui.QTreeWidgetItem()
            item.setText(0, module.name)
            item.vt_module = module
            self.item_module_map[item] = module
            
            if parent is not None:
                parent.addChild(item)
            else:
                self.treeWidget.addTopLevelItem(item)
            
            if module not in input_modules:
                for c in connections_to(pipeline, [module.id]):
                    add_to_tree(pipeline.modules[c.sourceId], item)
               
        for m_id in pipeline.modules:
            if len(connections_from(pipeline, [m_id])) == 0:
                add_to_tree(pipeline.modules[m_id])
                
        self.treeWidget.setCurrentItem(self.treeWidget.topLevelItem(0))

    def itemSelectionChanged(self):
        module = self.item_module_map[self.treeWidget.selectedItems()[0]]
        
        if self.module_widget is not None:
            self.horizontalLayout.removeWidget(self.module_widget)
            self.module_widget.deleteLater()
            self.module_widget = None
            
        registry = get_module_registry()
        
        widgetType = None
        widget = None

        # Try to get custom config widget for the module
        try:
            widgetType = registry.get_configuration_widget(
                    module.package, module.name, module.namespace)
        except ModuleRegistryException:
            pass

        if widgetType:
            # Use custom widget
            widget = widgetType(module, self.cell._controller)
            self.connect(widget, QtCore.SIGNAL("doneConfigure"),
                         self.configureDone)
            self.connect(widget, QtCore.SIGNAL("stateChanged"),
                         self.stateChanged)
        else:
            # Use PortsList widget, only if module has ports
            widget = DATPortsList(self)
            widget.update_module(module)
            if len(widget.port_spec_items) > 0:
                widget.set_controller(self.cell._controller)
            else:
                widget = None

        # Add widget to the layout
        if widget:
            self.module_widget = widget
            self.horizontalLayout.addWidget(widget)

    def stateChanged(self):
        pass

    def configureDone(self):
        pass

    def applyClicked(self):
        mngr = VistrailManager(self.cell._controller)
        pipeline = mngr.get_pipeline(self.cell.cellInfo)
        if pipeline.version != self.cell._controller.current_version:
            new_pipeline = PipelineInformation(
                    self.cell._controller.current_version,
                    pipeline.recipe,
                    pipeline.conn_map,
                    pipeline.port_map)
            mngr.created_pipeline(self.cell.cellInfo, new_pipeline)
            self.cell.update_pipeline(force_reexec=True)

    def okClicked(self):
        self.applyClicked()
        self.close()

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
