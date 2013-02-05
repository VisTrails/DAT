'''
Created on Feb 5, 2013

@author: benbu
'''
from PyQt4 import QtCore, QtGui
from vistrails.gui.ports_pane import PortsList
from dat.vistrail_data import VistrailManager
from dat import PipelineInformation
from dat.vistrails_interface import execute_pipeline_to_cell
from vistrails.core.modules.module_registry import get_module_registry,\
    ModuleRegistryException

class PlotConfigWindow(QtGui.QDialog):
    """This window houses the plot configuration widgets
    """
    def __init__(self, parent = None):
        QtGui.QDialog.__init__(self, parent)
        self.setLayout(QtGui.QVBoxLayout())
        
    def setPlotConfigWidget(self, widget):
        self.layout().takeAt(0)
        self.layout().addWidget(widget)
        
class PlotConfigEditor(object):
    """Base class mixin for high level plot editors
    
    Must implement setup(self, cell, plot), which is called
    when the widget is shown.
    """
    
    def setup(self, cell, plot):
        raise NotImplementedError
        
class DefaultPlotConfigEditor(QtGui.QWidget, PlotConfigEditor):
    """Default widget for editing 'advanced' plot settings. Shows
    PortList widget for each module in plot. If the module has an
    advanced editor, that is shown instead.
    """
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        
        self.tabWidget = QtGui.QTabWidget()
        
        btnApply = QtGui.QPushButton("&Apply")
        btnOk = QtGui.QPushButton("O&k")
        btnReset = QtGui.QPushButton("&Reset")
        
        btnApply.clicked.connect(self.applyClicked)
        btnOk.clicked.connect(self.okClicked)
        btnReset.clicked.connect(self.resetClicked)
        
        layoutButtons = QtGui.QHBoxLayout()
        layoutButtons.addWidget(btnReset)
        layoutButtons.addStretch()
        layoutButtons.addWidget(btnApply)
        layoutButtons.addWidget(btnOk)
        
        vLayout = QtGui.QVBoxLayout()
        vLayout.addWidget(self.tabWidget)
        vLayout.addLayout(layoutButtons)
        
        self.setLayout(vLayout)
        
        self.cell = None
        self.plot = None
    
    def setup(self, cell, plot):
        self.cell = cell
        self.plot = plot
        cellInfo = cell.cellInfo
        pipelineInfo = cellInfo.tab.getCellPipelineInfo(
                cellInfo.row, cellInfo.column)
        if pipelineInfo is not None:
            pipeline = PipelineInformation(pipelineInfo[0]['version'])
            recipe = VistrailManager(cell._controller).get_recipe(pipeline)

            self.tabWidget.clear()
            plot_modules = recipe.get_plot_modules(plot, 
                    cell._controller.current_pipeline)
            registry = get_module_registry()
            getter = registry.get_configuration_widget
            for module in plot_modules:
                widgetType = None
                widget = None
                #modeled after vistrails.gui.module_configuration.updateModule
                try:
                    widgetType = \
                        getter(module.package, module.name, module.namespace)
                except ModuleRegistryException:
                    pass
                if widgetType:
                    widget = widgetType(module, cell._controller)
                    self.connect(widget, QtCore.SIGNAL("doneConfigure"),
                                 self.configureDone)
                    self.connect(widget, QtCore.SIGNAL("stateChanged"),
                                 self.stateChanged)
                else:
                    widget = PortsList('input', self)
                    widget.update_module(module)
                    widget.set_controller(cell._controller)
                
                self.tabWidget.addTab(widget, module.name)
                
    def stateChanged(self):
        pass
    
    def configureDone(self):
        pass
            
    def applyClicked(self):
        #TODO: figure out why overlays no longer works, and make sure current version is
        # being tracked properly
        pipeline = PipelineInformation(self.cell._controller.current_version)
        execute_pipeline_to_cell(self.cell._controller, self.cell.cellInfo, pipeline)
        
    def okClicked(self):
        self.applyClicked()
        self.cell._plot_config_window.hide()
        
    def resetClicked(self):
        #TODO: if port list auto updates functions, need to reset pipeline to earlier version first
        self.setup(self.cell, self.plot)