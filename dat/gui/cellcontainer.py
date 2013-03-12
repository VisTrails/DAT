import warnings

from PyQt4 import QtCore, QtGui

from dat import MIMETYPE_DAT_VARIABLE, MIMETYPE_DAT_PLOT, DATRecipe
from dat.gui import get_icon
from dat.vistrail_data import VistrailManager
from dat import vistrails_interface
from dat.gui.overlays import PlotPromptOverlay, VariableDropEmptyCell, \
    PlotDroppingOverlay, VariableDroppingOverlay

from vistrails.core.application import get_vistrails_application
from vistrails.packages.spreadsheet.spreadsheet_cell import QCellContainer

class DATCellContainer(QCellContainer):
    """Cell container used in the spreadsheet.

    This is created by the spreadsheet for each cell, thus allowing us to tap
    into its behavior.
    It adds an overlay feature to the spreadsheet's cells and handles drops of
    variables and plots.
    """
    def __init__(self, cellInfo=None, widget=None, parent=None):
        self._variables = dict() # param name -> Variable
        self._constants = dict() # param name -> value: str
        self._plot = None # dat.vistrails_interface:Plot

        app = get_vistrails_application()
        app.register_notification(
                'dat_removed_variable', self._variable_removed)
        app.register_notification(
                'dragging_to_overlays', self._set_dragging)
        self._controller = app.get_controller()

        self._overlay = None
        self._overlay_scrollarea = QtGui.QScrollArea()
        self._overlay_scrollarea.setObjectName('overlay_scrollarea')
        self._overlay_scrollarea.setStyleSheet(
                'QScrollArea#overlay_scrollarea {'
                '    background-color: transparent;'
                '}'
                'Overlay {'
                '    background-color: transparent;'
                '}')
        self._overlay_scrollarea.setWidgetResizable(True)
        self._show_button = QtGui.QPushButton()
        self._show_button.setIcon(get_icon('show_overlay.png'))
        self._hide_button = QtGui.QPushButton()
        self._hide_button.setIcon(get_icon('hide_overlay.png'))

        QCellContainer.__init__(self, cellInfo, widget, parent)
        self.setAcceptDrops(True)

        self._overlay_scrollarea.setParent(self)

        self._show_button.setParent(self)
        self.connect(self._show_button, QtCore.SIGNAL('clicked()'),
                     self.show_overlay)
        self._show_button.setGeometry(self.width() - 24, 0, 24, 24)

        self._hide_button.setParent(self)
        self.connect(self._hide_button, QtCore.SIGNAL('clicked()'),
                     lambda: self._set_overlay(None))
        self._hide_button.setGeometry(self.width() - 24, 0, 24, 24)
        self._hide_button.setVisible(False)

        self.contentsUpdated()

    def setCellInfo(self, cellInfo):
        super(DATCellContainer, self).setCellInfo(cellInfo)

        if cellInfo is None: # We were removed from the spreadsheet
            app = get_vistrails_application()
            app.unregister_notification(
                    'dat_removed_variable', self._variable_removed)
            app.unregister_notification(
                    'dragging_to_overlays', self._set_dragging)

    def _set_dragging(self, dragging):
        """This is a hack to avoid an issue with Qt's mouse event propagation.

        If we don't set TransparentForMouseEvents on the overlay, when the drag
        enters, the overlay will receive the mouse event and propagate it to
        us. Thus it is on the call stack and we can't replace it with another
        overlay... It would cause a segmentation fault on Mac OS.
        """
        self._overlay_scrollarea.setAttribute(
                QtCore.Qt.WA_TransparentForMouseEvents, dragging)

    def _variable_removed(self, controller, varname, renamed_to=None):
        if controller != self._controller:
            return
        if self._plot is None:
            return
        if any(
                variable.name == varname
                for variable in self._variables.itervalues()):
            if renamed_to is None:
                # A variable was removed!
                # Two cases here:
                if self.widget() is not None:
                    # If this cell already contains a result, we'll just turn
                    # into a dumb VisTrails cell, as the DAT recipe doesn't
                    # exist anymore
                    self._plot = None
                    self._variables = dict()
                    self._constants = dict()
                else:
                    # If this cell didn't already contain a result, we just
                    # remove the associated parameters
                    # The user will just have to drop something else
                    to_remove = []
                    for param, variable in self._variables.iteritems():
                        if variable.name == varname:
                            to_remove.append(param)
                    for param in to_remove:
                        del self._variables[param]

                self._set_overlay(None)
            elif self._overlay is not None:
                self._overlay.update()

    def setWidget(self, widget):
        """Changes the current widget in the cell.

        This is called by the spreadsheet to put or remove a visualization in
        this cell.
        """
        super(DATCellContainer, self).setWidget(widget)
        if widget is None:
            return

        widget.raise_()
        self._show_button.raise_()

        self.contentsUpdated()

    def contentsUpdated(self):
        """Notifies that this cell's pipeline changed.

        This is called directly from the spreadsheet when a new visualization
        was set, but the cell widget was reused because it had the same type.
        The pipeline version still changed, so we need to update the overlay
        anyway.

        It is also called by setWidget() here.
        """
        if self.widget() is not None:
            # Get pipeline info from VisTrails
            pipelineInfo = self.cellInfo.tab.getCellPipelineInfo(
                    self.cellInfo.row, self.cellInfo.column)
            version = pipelineInfo[0]['version']
            pipeline = VistrailManager(self._controller).get_pipeline(version)
        else:
            # Get pipeline info from DAT: we might be building somethere here
            pipeline = VistrailManager(self._controller).get_pipeline(
                    self.cellInfo)

        if pipeline is not None:
            self._plot = pipeline.recipe.plot
            self._variables = dict(pipeline.recipe.variables)
            self._constants = dict(pipeline.recipe.constants)
        else:
            self._plot = None
            self._variables = dict()
            self._constants = dict()
        self._set_overlay(None)

    def _set_overlay(self, overlay_class, **kwargs):
        if overlay_class is None:
            # Default overlay
            if self.widget() is None and self._plot is not None:
                self._set_overlay(VariableDroppingOverlay, overlayed=False)
                return
            elif self.widget() is None:
                self._set_overlay(PlotPromptOverlay, overlayed=False)
                return

        if self._overlay is not None:
            self._overlay.setParent(None)
            self._overlay.deleteLater()

        if overlay_class is None:
            self._overlay = None
            self._overlay_scrollarea.lower()
            self._show_button.raise_()
            self._show_button.setVisible(self._plot is not None)
            self._hide_button.setVisible(False)
        else:
            self._overlay = overlay_class(self, **kwargs)
            self._overlay_scrollarea.setWidget(self._overlay)
            self._overlay.show()
            self._overlay_scrollarea.raise_()
            self._overlay_scrollarea.setGeometry(0, 0,
                                                 self.width(), self.height())
            self._show_button.setVisible(False)
            self._hide_button.setVisible(False)

    def show_overlay(self):
        """Shows the overlay from the button in the corner.

        It will remain shown until something gets dragged or the other button
        is clicked.
        """
        if self._plot is None:
            # Shouldn't happen
            return
        self._set_overlay(VariableDroppingOverlay, overlayed=False)
        self._hide_button.setVisible(True)
        self._hide_button.raise_()

    def resizeEvent(self, event):
        """Reacts to a resize by laying out the overlay and buttons.
        """
        super(DATCellContainer, self).resizeEvent(event)
        self._overlay_scrollarea.setGeometry(0, 0, self.width(), self.height())
        self._show_button.setGeometry(self.width() - 24, 0, 24, 24)
        self._hide_button.setGeometry(self.width() - 24, 0, 24, 24)

    def dragEnterEvent(self, event):
        mimeData = event.mimeData()
        if mimeData.hasFormat(MIMETYPE_DAT_VARIABLE):
            if self._plot is None:
                # We should ignore the drop here. That would make sense, and
                # display the correct mouse pointer
                # We can't though, because Qt would stop sending drag and drop
                # events
                # We still refuse the QDropEvent when the drop happens
                self._set_overlay(VariableDropEmptyCell, mimeData=mimeData)
            else:
                self._set_overlay(VariableDroppingOverlay, mimeData=mimeData)
        elif mimeData.hasFormat(MIMETYPE_DAT_PLOT):
            self._set_overlay(PlotDroppingOverlay, mimeData=mimeData)
        else:
            event.ignore()
            return
        event.accept()

    def dragMoveEvent(self, event):
        mimeData = event.mimeData()
        if (mimeData.hasFormat(MIMETYPE_DAT_VARIABLE) or
                mimeData.hasFormat(MIMETYPE_DAT_PLOT)):
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
            self._overlay.set_mouse_position(event.pos().x(), event.pos().y())
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self._set_overlay(None)

    def dropEvent(self, event):
        mimeData = event.mimeData()

        if mimeData.hasFormat(MIMETYPE_DAT_VARIABLE):
            if self._plot is not None and self._parameter_hovered is not None:
                event.accept()
                port_name = self._plot.ports[self._parameter_hovered].name
                varname = str(mimeData.data(MIMETYPE_DAT_VARIABLE))
                self._variables[port_name] = (VistrailManager(self._controller)
                                              .get_variable(varname))
                self.update_pipeline()
            else:
                event.ignore()

        elif mimeData.hasFormat(MIMETYPE_DAT_PLOT):
            event.accept()
            self._plot = mimeData.plot
            self._variables = dict()
            self._constants = dict()
            self._parameter_hovered = None
            self.update_pipeline()

        else:
            event.ignore()

        self._set_overlay(None)

    def remove_parameter(self, port_name):
        """Clear a parameter.

        Called from the overlay when a 'remove' button is clicked.
        """
        if self._plot is not None:
            del self._variables[port_name]
            self.update_pipeline()
            self._set_overlay(None)

    def change_constant(self, port_name, value):
        if self._constants.get(port_name) == value:
            return
        if value is None:
            del self._constants[port_name]
        else:
            self._constants[port_name] = value
        self.update_pipeline()

    def update_pipeline(self):
        """Updates the recipe and execute the workflow if enough ports are set.
        """
        # Look this recipe up in the VistrailData
        vistraildata = VistrailManager(self._controller)
        recipe = DATRecipe(self._plot, self._variables, self._constants)

        # Try to get an existing pipeline for this cell
        pipeline = vistraildata.get_pipeline(self.cellInfo)

        # No pipeline: build one
        if pipeline is None:
            pipeline = vistrails_interface.create_pipeline(
                    self._controller,
                    recipe,
                    self.cellInfo)
            vistraildata.created_pipeline(self.cellInfo, pipeline)

        # Pipeline with a different content: update it
        elif pipeline.recipe != recipe:
            try:
                pipeline = vistrails_interface.update_pipeline(
                        self._controller,
                        pipeline,
                        recipe)
            except vistrails_interface.UpdateError, e:
                warnings.warn("Could not update pipeline, creating new one:\n"
                              "%s" % e)
                pipeline = vistrails_interface.create_pipeline(
                        self._controller,
                        recipe,
                        self.cellInfo)
            vistraildata.created_pipeline(self.cellInfo, pipeline)

        # Execute the new pipeline if possible
        spreadsheet_tab = vistraildata.spreadsheet_tab
        tabWidget = spreadsheet_tab.tabWidget
        sheetname = tabWidget.tabText(tabWidget.indexOf(spreadsheet_tab))
        if not vistrails_interface.try_execute(
                self._controller,
                pipeline,
                sheetname,
                recipe) and self.widget() is not None:
            # Clear the cell
            self.cellInfo.tab.deleteCell(self.cellInfo.row,
                                         self.cellInfo.column)
