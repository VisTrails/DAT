import os, os.path

from PyQt4 import QtCore, QtGui

import dat.main


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


def get_icon(name):
    """Loads and return a QIcon.
    """
    # We might want to cache this
    return QtGui.QIcon(os.path.join(dat.main.application_path, 'dat/resources/icons', name))
