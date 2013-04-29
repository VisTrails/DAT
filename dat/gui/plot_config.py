from PyQt4 import QtCore, QtGui

from vistrails.core.application import get_vistrails_application
from vistrails.core.modules.module_registry import get_module_registry, \
    ModuleRegistryException
from vistrails.gui.ports_pane import PortsList, PortItem

from dat import PipelineInformation
from dat.vistrail_data import VistrailManager

cellModuleHistory = {}

class PlotConfigBase(QtGui.QDialog):
    """Base class for high level plot editors
    """
    
    def __init__(self, cell, *args, **kwargs):
        QtGui.QDialog.__init__(self, *args, **kwargs)
        self.cell = cell;
    
    def controller_changed(self, controller):
        if controller != self.cell._controller:
            self.close()
        
    def controller_closed(self, _):
        self.close()
        
    def version_changed(self, _):
        self.close()
        
    def closeEvent(self, event):
        QtGui.QWidget.closeEvent(self, event)
        self.unregister_notifications()
        print "Closing %s" % self.__class__.__name__
        #self.deleteLater()
        
    def sizeHint(self):
        return QtCore.QSize(640,480)
        
    def register_notifications(self):        
        app = get_vistrails_application()
        app.register_notification(
                'controller_changed',
                self.controller_changed)
        app.register_notification(
                'controller_closed',
                self.controller_closed)
        app.register_notification(
                'version_changed',
                self.version_changed)
        
    def unregister_notifications(self):      
        app = get_vistrails_application()
        app.unregister_notification(
                'controller_changed',
                self.controller_changed)
        app.unregister_notification(
                'controller_closed',
                self.controller_closed)
        app.unregister_notification(
                'version_changed',
                self.version_changed)
    
class DefaultPlotConfig(PlotConfigBase):
    """Default widget for editing 'advanced' plot settings.

    Shows PortList widget for each module in plot. If the module has an
    advanced editor, that is shown instead.
    """
    
    def __init__(self, cell, *args, **kwargs):
        PlotConfigBase.__init__(self, cell, *args, **kwargs)
        if cell not in cellModuleHistory:
            cellModuleHistory[cell] = None
        self.selectedItem = None
        self.setup_ui()
        
    def showEvent(self, event):
        PlotConfigBase.showEvent(self, event)
        self.setup_widgets()
        
    def setup_ui(self):

        self.setSizePolicy(QtGui.QSizePolicy.Ignored,
                           QtGui.QSizePolicy.Ignored)

        # Create tree widget
        self.treeWidget = QtGui.QTreeWidget()
        self.treeWidget.itemSelectionChanged.connect(self.itemSelectionChanged)
        
        #Create stacked widget
        self.stackedWidget = QtGui.QStackedWidget()
        
        # Create splitter for tree and stacked widget
        self.splitter = QtGui.QSplitter()
        self.splitter.addWidget(self.treeWidget)
        self.splitter.addWidget(self.stackedWidget)
        self.splitter.setStretchFactor(0,0)
        self.splitter.setStretchFactor(1,1)

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
        vLayout.addWidget(self.splitter)
        vLayout.addLayout(layoutButtons)

        self.setLayout(vLayout)
        self.resize(640,480)
        
    def setup_widgets(self):

        # Get pipeline of the cell
        pipelineInfo = self.cell.get_pipeline()
        self.config_version = pipelineInfo.version
        self.cell._controller.change_selected_version(self.config_version)
        pipeline = self.cell._controller.current_pipeline
        
        #clear old items
        self.treeWidget.clear()
        for i in reversed(range(self.stackedWidget.count())):
            self.stackedWidget.removeWidget(self.stackedWidget.widget(i))
        
        #get input modules
        input_modules = set(pipeline.modules[mod_id]
                            for lp in pipelineInfo.port_map.itervalues()
                            for mod_id, _ in lp)
        
        connections_from = self.cell._controller.get_connections_from
        connections_to = self.cell._controller.get_connections_to

        registry = get_module_registry()
        def add_to_tree_and_stack(module, parent=None):
            
            if module.name == "CellLocation":
                return
            
            # Try to get custom config widget for the module
            widgetType = None
            widget = None
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

            # Add to tree and stack
            if widget is not None:
                item = QtGui.QTreeWidgetItem()
                item.setText(0, module.name)
                if parent is not None:
                    parent.addChild(item)
                else:
                    self.treeWidget.addTopLevelItem(item)
                
                self.stackedWidget.addWidget(widget)
                item._mStackWidget = widget
                item._mModule = module
                if module == cellModuleHistory[self.cell]:
                    self.selectedItem = item
            else:
                item = parent
            
            if module not in input_modules:
                for c in connections_to(pipeline, [module.id]):
                    add_to_tree_and_stack(pipeline.modules[c.sourceId], item)
               
        for m_id in pipeline.modules:
            if len(connections_from(pipeline, [m_id])) == 0:
                add_to_tree_and_stack(pipeline.modules[m_id])
                
        if self.selectedItem is not None:
            self.treeWidget.setCurrentItem(self.selectedItem)

    def itemSelectionChanged(self):
        items = self.treeWidget.selectedItems()
        if len(items) > 0:
            self.stackedWidget.setCurrentWidget(items[0]._mStackWidget)
            cellModuleHistory[self.cell] = items[0]._mModule

    def stateChanged(self):
        pass

    def configureDone(self):
        pass

    def applyClicked(self):
        if QtGui.QApplication.focusWidget():
            QtGui.QApplication.focusWidget().clearFocus()
        mngr = VistrailManager(self.cell._controller)
        pipeline = self.cell.get_pipeline()
        print 'cfg: %d cell: %d ctrl: %d' % (self.config_version, 
                                             pipeline.version,
                                             self.cell._controller.current_version)
        if (self.config_version == pipeline.version !=
                self.cell._controller.current_version):
            self.config_version = self.cell._controller.current_version
            new_pipeline = PipelineInformation(
                    self.cell._controller.current_version,
                    pipeline.recipe,
                    pipeline.conn_map,
                    pipeline.port_map)
            mngr.created_pipeline(self.cell.cellInfo, new_pipeline)
            self.cell.update_pipeline(new_pipeline=new_pipeline)

    def okClicked(self):
        self.applyClicked()
        self.close()

    def resetClicked(self):
        if QtGui.QApplication.focusWidget():
            QtGui.QApplication.focusWidget().clearFocus()
        pipeline = self.cell.get_pipeline()
        if (self.config_version == pipeline.version !=
                self.cell._controller.current_version):
            self.cell._controller.change_selected_version(self.config_version)
        self.setup_widgets()
        #TODO: select last item in tree

    def version_changed(self, version):
        if (self.config_version != version):
            if not self.isActiveWindow():
                print 'closing widget, version changed while "%s" had focus' % str(QtGui.QApplication.focusWidget())
                self.close()
        

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
