'''
Created on Feb 5, 2013

@author: benbu
'''
from PyQt4 import QtCore, QtGui
from vistrails.gui.ports_pane import PortsList
from dat.vistrail_data import VistrailManager
from vistrails.core.modules.module_registry import get_module_registry,\
    ModuleRegistryException
from dat.gui.overlays import Overlay

#class PlotConfigWindow(QtGui.QDialog):
#    """This window houses the plot configuration widgets
#    """
#    def __init__(self, parent = None):
#        QtGui.QDialog.__init__(self, parent)
#        self.setLayout(QtGui.QVBoxLayout())
#        
#    def setPlotConfigWidget(self, widget):
#        """Replaces current widget if one exists
#        """
#        widgetItem = self.layout().takeAt(0)
#        if widgetItem:
#            widgetItem.widget().close()
#        self.layout().addWidget(widget)
        
class PlotConfigOverlay(Overlay):
    """Base class for high level plot editors
    
    Must implement setup(self, cell, plot), which is called
    when the widget is shown.
    """
    
    def setup(self, cell, plot):
        raise NotImplementedError
        
class DefaultPlotConfigOverlay(PlotConfigOverlay):
    """Default widget for editing 'advanced' plot settings. Shows
    PortList widget for each module in plot. If the module has an
    advanced editor, that is shown instead.
    """
    def __init__(self, cellcontainer):
        Overlay.__init__(self, cellcontainer, False)
        
        #create tab widget
        self.tabWidget = QtGui.QTabWidget()
        
        #create buttons
        btnApply = QtGui.QPushButton("&Apply")
        btnOk = QtGui.QPushButton("O&k")
        btnReset = QtGui.QPushButton("&Reset")
        
        #connect buttons
        btnApply.clicked.connect(self.applyClicked)
        btnOk.clicked.connect(self.okClicked)
        btnReset.clicked.connect(self.resetClicked)
        
        #add buttons to layout
        layoutButtons = QtGui.QHBoxLayout()
        layoutButtons.addWidget(btnReset)
        layoutButtons.addStretch()
        layoutButtons.addWidget(btnApply)
        layoutButtons.addWidget(btnOk)
        
        #add tabwidget above buttons
        vLayout = QtGui.QVBoxLayout()
        vLayout.addWidget(self.tabWidget)
        vLayout.addLayout(layoutButtons)
        
        self.setLayout(vLayout)
        
        self.cell = None
        self.plot = None
    
    def setup(self, cell, plot):
        self.cell = cell
        self.plot = plot
        
        #get pipeline of the cell
        mngr = VistrailManager(cell._controller)
        pipeline = mngr.get_pipeline(cell.cellInfo)
        
        #clear old tabs
        self.tabWidget.clear()
        
        #get all of the plot modules in the pipeline
        plot_modules = pipeline.recipe.get_plot_modules(plot, 
                cell._controller.current_pipeline)
        
        
        registry = get_module_registry()
        getter = registry.get_configuration_widget
        for module in plot_modules:
            widgetType = None
            widget = None
            
            #try to get custom config widget for the module
            try:
                widgetType = \
                    getter(module.package, module.name, module.namespace)
            except ModuleRegistryException:
                pass
            
            if widgetType:
                #use custom widget
                widget = widgetType(module, cell._controller)
                self.connect(widget, QtCore.SIGNAL("doneConfigure"),
                             self.configureDone)
                self.connect(widget, QtCore.SIGNAL("stateChanged"),
                             self.stateChanged)
            else:
                #use PortsList widget
                widget = PortsList('input', self)
                widget.update_module(module)
                widget.set_controller(cell._controller)
            
            #add widget in new tab
            self.tabWidget.addTab(widget, module.name)
                
    def stateChanged(self):
        pass
    
    def configureDone(self):
        pass
            
    def applyClicked(self):
        mngr = VistrailManager(self.cell._controller)
        pipeline = mngr.get_pipeline(self.cell.cellInfo)
        pipeline.version = self.cell._controller.current_version
        self.cell.update_pipeline()
        
    def okClicked(self):
        self.applyClicked()
        self.cell._set_overlay(None)
        
    def resetClicked(self):
        self.setup(self.cell, self.plot)