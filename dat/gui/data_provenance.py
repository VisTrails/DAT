from PyQt4 import QtCore, QtGui

import warnings

from dat import data_provenance
from dat.gui import translate
from dat.gui.generic import ZoomPanGraphicsView
from dat.vistrail_data import VistrailManager


X_MARGIN = 100
Y_MARGIN = 100
X_PADDING = 10
Y_PADDING = 3


class ProvenanceItem(QtGui.QGraphicsItem):
    text_font = QtGui.QFont()

    def __init__(self, label):
        QtGui.QGraphicsItem.__init__(self)
        self._label = label
        self.links = set()
        metrics = QtGui.QFontMetrics(self.text_font)
        width = metrics.width(label) + X_PADDING * 2
        height = metrics.height() + Y_PADDING * 2
        self._rect = QtCore.QRectF(-width/2, -height/2,
                                   width, height)

    def boundingRect(self):
        return self._rect

    def paint(self, painter, option, widget=None):
        painter.setBrush(self.background_color)
        painter.setPen(QtGui.QColor(0, 0, 0))
        self.draw_shape(painter, self._rect)
        painter.setPen(QtGui.QColor(0, 0, 0))
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.setFont(self.text_font)
        painter.drawText(self._rect, QtCore.Qt.AlignCenter, self._label)

    def draw_shape(self, painter, rect):
        painter.drawRoundedRect(rect, 8, 8)


class OperationProvenanceItem(ProvenanceItem):
    background_color = QtGui.QColor(237, 222, 222)


class VariableProvenanceItem(ProvenanceItem):
    background_color = QtGui.QColor(180, 220, 250)

    def draw_shape(self, painter, rect):
        painter.drawRect(rect)


class LoaderProvenanceItem(ProvenanceItem):
    background_color = QtGui.QColor(225, 225, 225)


class ConstantProvenanceItem(ProvenanceItem):
    background_color = QtGui.QColor(250, 250, 164)

    def __init__(self, value):
        value = repr(value)
        if len(value) > 10:
            value = value[:7] + '...'
        ProvenanceItem.__init__(self, value)

    def draw_shape(self, painter, rect):
        painter.drawEllipse(rect)


class ProvenanceSceneLayout(object):
    class TmpNode(object):
        def __init__(self, item, row, links):
            self.item = item
            self.row = row
            self.links = links
            self.pos = 0
            self.nb_pos = 0

        def add_pos(self, pos):
            self.pos += pos
            self.nb_pos += 1

    def __init__(self, controller):
        self.nodes = dict() # prov -> TmpNode
        self._controller = controller

    def populate(self, provenance, row=0):
        if row == 0:
            self.root = provenance

        try:
            node = self.nodes[provenance]
        except KeyError:
            pass
        else:
            if node.row <= row:
                node.row = row + 1
            return node.item

        item = None
        links = set()
        if isinstance(provenance, data_provenance.Operation):
            item = OperationProvenanceItem(provenance['name'])
            for arg in provenance['args'].itervalues():
                self.populate(arg, row+1)
                links.add(arg)
        elif isinstance(provenance, data_provenance.Variable):
            varname = self._controller.vistrail.get_tag(provenance['version'])
            vistraildata = VistrailManager(self._controller)
            prev = vistraildata.variable_provenance(provenance['version'])
            if prev is None:
                # We are missing data! Someone tampered with the vistrail?
                if varname is not None and varname[:8] == 'dat-var':
                    varname = varname[:8]
                else:
                    varname = translate(ProvenanceSceneLayout)(
                            '(deleted variable)')
                warnings.warn(
                        "A variable (version %r) referenced from provenance "
                        "is missing!" % provenance['version'])
                item = VariableProvenanceItem(varname)
            elif varname is not None and varname[:8] == 'dat-var-':
                self.populate(prev, row+1)
                varname = varname[8:]
                item = VariableProvenanceItem(varname)
                links.add(prev)
            else:
                # If that variable has been deleted, we just skip it, like an
                # intermediate result
                self.populate(prev, row)
        elif isinstance(provenance, data_provenance.Loader):
            item = LoaderProvenanceItem(provenance['name'])
        elif isinstance(provenance, data_provenance.Constant):
            item = ConstantProvenanceItem(provenance['constant'])
        else:
            raise TypeError("populate() got %r" % (provenance,))

        if item is not None:
            self.nodes[provenance] = self.TmpNode(item, row, links)

    def addToScene(self, scene, sink=None):
        # Assign nodes to rows
        rows = {}
        nb_rows = 0
        for node in self.nodes.itervalues():
            rows.setdefault(node.row, []).append(node)
            if node.row + 1 > nb_rows:
                nb_rows = node.row + 1

        # Order nodes on each row
        for row in xrange(nb_rows):
            nodes = rows[row]
            for node in nodes:
                if node.nb_pos > 0:
                    node.pos /= float(node.nb_pos)

            # Order nodes
            nodes = sorted(rows[row], key=lambda n: n.pos)
            xs = -X_MARGIN * (len(nodes) - 1)/2
            for i, node in enumerate(nodes):
                x = xs + i * X_MARGIN
                node.item.setPos(x, -row * Y_MARGIN)
                for up in node.links:
                    up = self.nodes[up]
                    up.add_pos(x)

        # Adds the items to the scene
        for node in self.nodes.itervalues():
            scene.addItem(node.item)
            # Adds the edges
            for prov in node.links:
                other = self.nodes[prov]
                a = node.item.pos()
                b = other.item.pos()
                line_item = scene.addLine(a.x(), a.y(), b.x(), b.y())
                line_item.setZValue(-1)

        if sink is not None:
            item = VariableProvenanceItem(sink)
            item.setPos(0, Y_MARGIN)
            scene.addItem(item)
            line_item = scene.addLine(0, Y_MARGIN, 0, 0)
            line_item.setZValue(-1)


class DataProvenancePanel(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)

        _ = translate(DataProvenancePanel)

        self._scene = None
        self._viewer = QtGui.QLabel(_("Select a variable to display its "
                                      "provenance"))
        self._viewer.setWordWrap(True)
        self._viewer.setAlignment(QtCore.Qt.AlignCenter)

        layout = QtGui.QVBoxLayout()
        layout.addWidget(self._viewer)
        self.setLayout(layout)

    @QtCore.pyqtSlot('PyQt_PyObject')
    def showVariable(self, variable):
        if self._viewer is not None:
            self._viewer.deleteLater()
            self._viewer = self._scene = None

        if variable is None:
            return

        self._scene = QtGui.QGraphicsScene()
        self._viewer = ZoomPanGraphicsView(self._scene)

        self.layout().addWidget(self._viewer)

        # Create the scene recursively, starting at the bottom
        layout = ProvenanceSceneLayout(variable._controller)
        layout.populate(variable.provenance)
        layout.addToScene(self._scene, sink=variable.name)
