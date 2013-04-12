from PyQt4 import QtCore, QtGui

from dat.gui import translate
from dat.gui.generic import ZoomPanGraphicsView


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

        # TODO : create scene
