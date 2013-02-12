from PyQt4 import QtCore, QtGui

from dat.gui.overlays import Overlay

from dat import MIMETYPE_DAT_VARIABLE
from dat.gui import get_icon
from dat.vistrail_data import VistrailManager


class VariableDroppingOverlay(Overlay):
    """The main overlay.

    Displays targets for each parameter, according to the current plot, and
    type-checks them.
    """

    def __init__(self, cellcontainer, mimeData=None, forced=False):
        Overlay.__init__(self, cellcontainer)

        self._forced = forced
        if forced:
            self._remove_icon = get_icon('remove_parameter.png')

        # Type-checking, so we can show which parameters are suitable to
        # receive the drop
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

                # Display a button to remove this parameter
                if self._forced:
                    self._remove_icon.paint(
                            qp,
                            30 + self._parameter_max_width,
                            y + height,
                            16, 16)
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

    def resizeEvent(self, event):
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
            self.repaint()

    def mouseReleaseEvent(self, event):
        metrics = self._cell.fontMetrics()
        height = metrics.height()

        for i, port in enumerate(self._cell._plot.ports):
            port_y, port_h = self._parameters[i]

            variable = self._cell._variables.get(port.name)
            if variable is not None:
                btn_x = 30 + self._parameter_max_width
                btn_y = port_y + height
                if (btn_x <= event.x() < btn_x + 16 and
                        btn_y <= event.y() < btn_y + 16):
                    # Button pressed: remove parameter
                    self._cell.remove_parameter(port.name)
                    break
