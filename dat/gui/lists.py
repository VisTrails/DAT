from PyQt4 import QtCore, QtGui


class DraggableListWidget(QtGui.QListWidget):
    def __init__(self, parent=None, mimetype='text/plain'):
        QtGui.QListWidget.__init__(self, parent)
        self._mime_type = mimetype
        self.setDragEnabled(True)
        self.setDragDropMode(QtGui.QAbstractItemView.DragOnly)

    def buildData(self, element):
        data = QtCore.QMimeData()
        data.setData(self._mime_type,
                     element.text().toAscii())
        data.pwetpwet = 42
        return data

    def startDrag(self, actions):
        indexes = self.selectedIndexes()
        if len(indexes) == 1:
            data = self.buildData(self.itemFromIndex(indexes[0]))

            drag = QtGui.QDrag(self)
            drag.setMimeData(data)
            drag.start(QtCore.Qt.CopyAction)
