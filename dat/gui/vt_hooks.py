from PyQt4 import QtCore, QtGui

from dat.gui import translate
from dat.vistrail_data import VistrailManager


def _color_version_nodes(node, action, tag, description):
    pipelineInfo = None
    if action is not None and VistrailManager.initialized:
        vistraildata = VistrailManager()
        # Warning: the first scene might get created before the
        # VistrailManager gets the 'controller_changed' signal, thus
        # VistrailManager() might be None
        if vistraildata is not None:
            pipelineInfo = vistraildata.get_pipeline(action.id)

    if tag == 'dat-vars':
        # Variable root
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        return dict(
                VERSION_USER_BRUSH=brush,
                VERSION_OTHER_BRUSH=brush,
                VERSION_LABEL_COLOR=QtGui.QColor(255, 255, 255),
                VERSION_SHAPE='rectangle')
    elif tag is not None and tag.startswith('dat-var-'):
        # Variables
        return dict(
                VERSION_USER_BRUSH=QtGui.QBrush(QtGui.QColor(27, 27, 75)),
                VERSION_OTHER_BRUSH=QtGui.QBrush(QtGui.QColor(72, 50, 25)),
                VERSION_LABEL_COLOR=QtGui.QColor(255, 255, 255),
                VERSION_SHAPE='rectangle')
    elif pipelineInfo is not None:
        return dict(
                VERSION_USER_BRUSH=QtGui.QBrush(QtGui.QColor(171, 169, 214)),
                VERSION_OTHER_BRUSH=QtGui.QBrush(QtGui.QColor(219, 198, 179)))
    else:
        return dict()


def _get_custom_version_panels(controller, version):
    _ = translate("recipe_version_panel")

    if VistrailManager.initialized:
        pipelineInfo = VistrailManager(controller).get_pipeline(version)
        if pipelineInfo is not None:
            monospace = QtGui.QFont('Monospace')
            monospace.setStyleHint(QtGui.QFont.TypeWriter)

            recipe = pipelineInfo.recipe
            recipe_widget = QtGui.QGroupBox(_("DAT recipe"))
            recipe_widget.setSizePolicy(
                    recipe_widget.sizePolicy().horizontalPolicy(),
                    QtGui.QSizePolicy.Fixed)
            layout = QtGui.QVBoxLayout()

            line = QtGui.QHBoxLayout()
            line.addWidget(QtGui.QLabel(_("Plot:")))
            plot_label = QtGui.QLabel("%s" % recipe.plot.name)
            plot_label.setFont(monospace)
            line.addWidget(plot_label)
            layout.addLayout(line)

            layout.addWidget(QtGui.QLabel(_("Variables:")))
            variable_list = QtGui.QTextEdit()
            color = variable_list.textColor()
            variable_list.setEnabled(False)
            variable_list.setTextColor(color)
            variable_list.setFont(monospace)
            variable_list.setLineWrapMode(QtGui.QTextEdit.NoWrap)
            variable_list.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
            variable_list.setPlainText(
                    '\n'.join(v.name
                              for v in recipe.variables.itervalues()))
            variable_list.setFixedHeight(
                    variable_list.document().size().height())
            layout.addWidget(variable_list)

            recipe_widget.setLayout(layout)
            return [(-1, recipe_widget)]
    return []


hooks = dict(
        version_node_theme=_color_version_nodes,
        version_prop_panels=_get_custom_version_panels)
