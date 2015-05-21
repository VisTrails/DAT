import os

from PyQt4 import QtCore, QtGui

import dat.main

from vistrails.core.application import get_vistrails_application


class _DraggingToOverlaysLock(object):
    """This is a mechanism used to disable mouse events on overlays.

    Because Qt mouse events propagate from the bottom up (if ignored, it gets
    passed to the parent), if overlays are not transparent for mouse events,
    they are in the call stack when the cell container removes them, which can
    cause a segmentation fault. This happens at least on Mac OS.

    This mechanism allows overlays to set WA_TransparentForMouseEvents for the
    duration of the drag which works around the issue.
    """
    def __init__(self):
        get_vistrails_application().create_notification('dragging_to_overlays')

    def __enter__(self):
        get_vistrails_application().send_notification('dragging_to_overlays',
                                                      True)

    def __exit__(self, exc_type, exc_val, exc_tb):
        get_vistrails_application().send_notification('dragging_to_overlays',
                                                      False)


_dragging_lock = None


def dragging_to_overlays():
    global _dragging_lock
    if _dragging_lock is None:
        _dragging_lock = _DraggingToOverlaysLock()
    return _dragging_lock


def translate(context):
    """Builds a translator function for a given context.

    QObject#trUtf8() is bugged, as it uses the context of the lowest subclass
    (instead of the class defining the method where it is actually called).
    This is different from C++ and will cause issues.

    You might want to do something like this:
        _ = dat.gui.translate(ThisClass)
    At the beginning of a internationalized method, and use _() to mark
    localizable strings.
    """
    if isinstance(context, type):
        context = context.__module__ + '.' + context.__name__

    def tr(sourceText, disambiguation=None):
        return unicode(QtCore.QCoreApplication.translate(
                context,
                sourceText,
                disambiguation,
                QtCore.QCoreApplication.UnicodeUTF8))

    return tr


_icon_cache = dict()


def get_icon(name):
    """Loads and return a QIcon.
    """
    # We might want to cache this
    try:
        return _icon_cache[name]
    except KeyError:
        icon = QtGui.QIcon(os.path.join(dat.main.application_path,
                                        'dat/resources/icons',
                                        name))
        _icon_cache[name] = icon
        return icon
