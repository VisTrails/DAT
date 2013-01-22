from PyQt4 import QtCore, QtGui

from dat import MIMETYPE_DAT_VARIABLE, MIMETYPE_DAT_PLOT, \
    DATRecipe, PipelineInformation
from dat.gui import translate
from dat.manager import Manager
from dat.plot_map import PlotMap
from dat import vistrails_interface

from vistrails.packages.spreadsheet.spreadsheet_cell import QCellContainer


class Overlay(object):
    """Base class for the cell overlays.
    """

    def __init__(self, cellcontainer, mimeData):
        self._cell = cellcontainer

    # Background of all overlay (translucent, on top of the cell's content)
    background = QtGui.QColor(255, 255, 255, 127)
    # Accepting a drop
    ok_pen      = QtGui.QColor(102, 153, 255)
    ok_fill     = QtGui.QColor(187, 204, 255)
    # Denying a drop
    no_pen      = QtGui.QColor(255,  51,  51)
    no_fill     = QtGui.QColor(255, 170, 170)
    # Hovered
    targeted    = QtGui.QColor(255, 255, 255)
    # Text (black)
    text        = QtGui.QColor(0, 0, 0)

    def draw(self, qp):
        qp.fillRect(
                0, 0,
                self._cell.width(), self._cell.height(),
                Overlay.background)

    def set_mouse_position(self, x, y):
        pass

    def resize(self, width, height):
        pass


class VariableDropEmptyCell(Overlay):
    """Used when dragging a variable over a cell without a plot.

    A plot must be dropped first, so that the types of the parameters are
    known.
    """

    def draw(self, qp):
        _ = translate(VariableDropEmptyCell)

        Overlay.draw(self, qp)

        qp.setPen(Overlay.no_pen)
        qp.setBrush(Overlay.no_fill)
        qp.drawRect(
                10, 10,
                self._cell.width() - 20, self._cell.height() - 20)

        qp.drawText(
                10, 10,
                self._cell.width() - 20, self._cell.height() - 20,
                QtCore.Qt.AlignCenter | QtCore.Qt.TextWordWrap,
                _("You need to drag a plot first"))


class PlotDroppingOverlay(Overlay):
    """Shown when dragging a plot in a cell.

    Just provides feedback for the user.
    """

    def __init__(self, cellcontainer, mimeData):
        _ = translate(PlotDroppingOverlay)

        Overlay.__init__(self, cellcontainer, mimeData)

        if cellcontainer._plot is None:
            text = _("Drop here to add a {plotname} to this cell")
        else:
            text = _("Drop here to replace this plot with a new {plotname}")
        self._text = text.format(
                plotname=mimeData.plot.name)

    def draw(self, qp):
        Overlay.draw(self, qp)

        qp.setPen(Overlay.ok_pen)
        qp.setBrush(Overlay.ok_fill)
        qp.drawRect(
                10, 10,
                self._cell.width() - 20, self._cell.height() - 20)

        qp.drawText(
                10, 10,
                self._cell.width() - 20, self._cell.height() - 20,
                QtCore.Qt.AlignCenter | QtCore.Qt.TextWordWrap,
                self._text)


class VariableDroppingOverlay(Overlay):
    """The main overlay.

    Displays targets for each parameter, according to the current plot, and
    type-checks them.
    """

    def __init__(self, cellcontainer, mimeData):
        Overlay.__init__(self, cellcontainer, mimeData)

        self.resize(cellcontainer.width(), cellcontainer.height())

        # Type-checking, so we can show which parameters are suitable to
        # receive the drop
        if not mimeData or not mimeData.hasFormat(MIMETYPE_DAT_VARIABLE):
            self._compatible_ports = None
        else:
            varname = str(mimeData.data(MIMETYPE_DAT_VARIABLE))
            variable = Manager().get_variable(varname)
            self._compatible_ports = [
                    port is None or issubclass(variable.type, port.type)
                    for port in self._cell._plot.ports]

        self._cell._parameter_hovered = None

    def draw(self, qp):
        Overlay.draw(self, qp)

        qp.setPen(Overlay.text)
        qp.setBrush(QtCore.Qt.NoBrush)
        metrics = qp.fontMetrics()
        ascent = metrics.ascent()
        height = metrics.height()
        normalFont = qp.font()
        requiredFont = QtGui.QFont(qp.font())
        requiredFont.setBold(True)

        # Plot name
        qp.drawText(5, 5 + ascent, self._cell._plot.name + " (")

        for i, port in enumerate(self._cell._plot.ports):
            y, h = self._parameters[i]

            # Draw boxes according to the compatibility of the port with the
            # variable being dragged
            if self._compatible_ports:
                if self._compatible_ports[i]:
                    qp.setPen(Overlay.ok_pen)
                    qp.setBrush(Overlay.ok_fill)
                else:
                    qp.setPen(Overlay.no_pen)
                    qp.setBrush(Overlay.no_fill)
                qp.drawRect(20, y, self._parameter_max_width, h)

            qp.setBrush(QtCore.Qt.NoBrush)
            if i == self._cell._parameter_hovered:
                qp.setPen(Overlay.targeted)
            else:
                qp.setPen(Overlay.text)

            # The parameter is either set, required or optional
            variable = self._cell._variables.get(port.name)
            if variable is not None:
                qp.setFont(normalFont)
                qp.drawText(40, y + height + ascent, " = %s" % variable.name)
            elif port.optional:
                qp.setFont(normalFont)
            else:
                qp.setFont(requiredFont)
            qp.drawText(20, y + ascent, port.name)

        # Closing parenthesis
        qp.setPen(Overlay.text)
        qp.drawText(
                5,
                self._parameters[-1][0] + self._parameters[-1][1] + ascent,
                ")")

    def resize(self, width, height):
        metrics = self._cell.fontMetrics()
        height = metrics.height()

        fontBold = QtGui.QFont(self._cell.font())
        fontBold.setBold(True)
        metricsBold = QtGui.QFontMetrics(fontBold)
        heightBold = metricsBold.height()

        y = 5 # Top margin
        y += height # Plot name

        # Position the parameters
        self._parameters = []
        maxwidth = 0
        for port in self._cell._plot.ports:
            variable = self._cell._variables.get(port.name)
            if variable is not None:
                width = 20 + metrics.width(" = %s" % variable.name)
                h = height * 2
            elif port.optional:
                width = metrics.width(port.name)
                h = height
            else:
                width = metricsBold.width(port.name)
                h = heightBold
            self._parameters.append((y, h))
            y += h
            if width > maxwidth:
                maxwidth = width
        self._parameter_max_width = maxwidth

    def set_mouse_position(self, x, y):
        # Find the currently targeted port: the compatible port closer to the
        # mouse

        if not self._compatible_ports:
            return # Nothing to target

        targeted, mindist = None, None
        for i, param in enumerate(self._parameters):
            if self._compatible_ports[i]:
                if y < param[0]:
                    dist = param[0] - y
                elif y > param[0] + param[1]:
                    dist = y - (param[0] + param[1])
                else:
                    targeted = i
                    break
                if mindist is None or dist < mindist:
                    mindist = dist
                    targeted = i

        if self._cell._parameter_hovered != targeted:
            self._cell._parameter_hovered = targeted
            self._cell.repaint()


class PlotPromptOverlay(Overlay):
    """Default content of the overlayed cells.

    Simply displays a prompt asking the user to drop a plot in the cell.
    """

    def draw(self, qp):
        _ = translate(PlotPromptOverlay)

        qp.setPen(Overlay.text)
        qp.setBrush(QtCore.Qt.NoBrush)
        qp.drawText(
                10, 10,
                self._cell.width() - 20, self._cell.height() - 20,
                QtCore.Qt.AlignCenter | QtCore.Qt.TextWordWrap,
                _("Drag a plot in this cell"))


class DATCellContainer(QCellContainer):
    """Cell container used in the spreadsheet.

    This is created by the spreadsheet for each cell, thus allowing us to tap
    into its behavior.
    It adds an overlay feature to the spreadsheet's cells and handles drops of
    variables and plots.
    """
    def __init__(self, cellInfo=None, widget=None, parent=None):
        self._overlay = None
        self._variables = dict() # param name -> Variable
        self._plot = None # dat.vistrails_interface:Plot

        QCellContainer.__init__(self, cellInfo, widget, parent)

        self.setAcceptDrops(True)

        self._set_overlay(None)

        Manager().add_variable_observer((None, self._variable_removed))

    def _variable_removed(self, varname, renamed_to=None):
        if renamed_to is None:
            # A variable was removed!
            if any(
                    variable.name == varname
                    for variable in self._variables.itervalues()):
                # Two cases here:
                if self.widget() is not None:
                    # If this cell already contains a result, we'll just turn
                    # into a dumb VisTrails cell, as the DAT recipe doesn't
                    # exist anymore
                    self._plot = None
                    self._variables = dict()
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

    def setWidget(self, widget):
        super(DATCellContainer, self).setWidget(widget)
        if widget is None:
            return

        widget.lower()

        pipelineInfo = self.cellInfo.tab.getCellPipelineInfo(
                self.cellInfo.row, self.cellInfo.column)
        if pipelineInfo is not None:
            recipe = pipelineInfo and PlotMap().get_recipe(
                    PipelineInformation(pipelineInfo[0]['version']))
        else:
            recipe = None
        if recipe is not None:
            self._plot = recipe.plot
            self._variables = list(recipe.variables)
        else:
            self._plot = None
            self._variables = dict()
        self._set_overlay(None)

    def _set_overlay(self, overlay_class, mimeData=None):
        if overlay_class is None:
            # Default overlay
            if self.widget() is None and self._plot is not None:
                self._set_overlay(VariableDroppingOverlay)
            elif self.widget() is None:
                self._set_overlay(PlotPromptOverlay)
            elif self._overlay is not None:
                self._overlay = None
        else:
            self._overlay = overlay_class(self, mimeData)
        self.repaint()

    def resizeEvent(self, event):
        super(DATCellContainer, self).resizeEvent(event)
        if self._overlay is not None:
            self._overlay.resize(self.width(), self.height())

    def dragEnterEvent(self, event):
        mimeData = event.mimeData()
        if mimeData.hasFormat(MIMETYPE_DAT_VARIABLE):
            if self._plot is None:
                # We should ignore the drop here. That would make sense, and
                # display the correct mouse pointer
                # We can't though, because Qt would stop sending drag and drop
                # events
                # We still refuse the QDropEvent when the drop happens
                self._set_overlay(VariableDropEmptyCell, mimeData)
            else:
                self._set_overlay(VariableDroppingOverlay, mimeData)
        elif mimeData.hasFormat(MIMETYPE_DAT_PLOT):
            self._set_overlay(PlotDroppingOverlay, mimeData)
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
            if self._plot and self._parameter_hovered is not None:
                event.accept()
                port_name = self._plot.ports[self._parameter_hovered].name
                self._variables[port_name] = (
                        Manager().get_variable(
                                str(mimeData.data(MIMETYPE_DAT_VARIABLE))))
                self.try_update()
            else:
                event.ignore()

        elif mimeData.hasFormat(MIMETYPE_DAT_PLOT):
            event.accept()
            self._plot = mimeData.plot
            self._variables = {}
            self._parameter_hovered = None
            # Deleting a plot must update the pipeline infos in the spreadsheet
            # tab
            # StandardWidgetSheetTabInterface#deleteCell()
            self.try_update()

        else:
            event.ignore()

        self._set_overlay(None)

    def paintEvent(self, event):
        QCellContainer.paintEvent(self, event)

        if self._overlay:
            self._overlay.draw(QtGui.QPainter(self))

    def try_update(self):
        """Check if enough ports are set, and execute the workflow
        """
        if all(
                port.optional or self._variables.has_key(port.name)
                for port in self._plot.ports):
            # Look this recipe up in the PlotMap
            recipe = DATRecipe(self._plot, self._variables)
            pipeline = PlotMap().get_pipeline(recipe)
            if pipeline is None:
                # Build the pipeline
                pipeline = vistrails_interface.create_pipeline(recipe)
                PlotMap().created_pipeline(recipe, pipeline)
            vistrails_interface.execute_pipeline_to_cell(self.cellInfo,
                                                         pipeline)
