from PyQt4 import QtGui

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
    if VistrailManager.initialized:
        pipelineInfo = VistrailManager(controller).get_pipeline(version)
        if pipelineInfo is not None:
            recipe = pipelineInfo.recipe
            text_widget = QtGui.QTextEdit(
                    "DAT Plot<br/>"
                    "%s<br/>"
                    "Variables:<br/>"
                    "%s" % (
                    recipe.plot.name,
                    '<br/>'.join(recipe.variables)))
            text_widget.setMaximumHeight(
                    text_widget.fontMetrics().height() * (
                            3 + len(recipe.variables)) +
                    text_widget.contentsMargins().top() +
                    text_widget.contentsMargins().bottom())
            return (
                    [(-1, QtGui.QLabel("DAT Plot %r" % recipe.plot.name)),
                     (-1, QtGui.QLabel("Variables:"))] +
                    [(-1, QtGui.QLabel("  %s" % v.name))
                     for v in recipe.variables.itervalues()])
    return []


hooks = dict(
        version_node_theme=_color_version_nodes,
        version_prop_panels=_get_custom_version_panels)
