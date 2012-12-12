import sys
from PyQt4 import QtGui

from dat.gui.window import MainWindow

import vistrails.core.requirements


def start():
    app = QtGui.QApplication(sys.argv)

    # -----
    # We need to initialize VisTrails here, but don't want to use its
    # QApplication, single-instance code, splash screen or usual running modes
    # We don't want anything to appear either, we just want to embed the
    # spreadsheet window
    # I believe this requires changes in VisTrails

    try:
        vistrails.core.requirements.check_all_vistrails_requirements()
    except vistrails.core.requirements.MissingRequirement, e:
        QtGui.QMessageBox.critical(
                None,
                _("Missing requirement"),
                str(_("VisTrails reports that a requirement is missing.\n"
                      "This application can't continue without {required}."))
                        .format(required=e.requirement))
        return 1

    # VistrailsApplicationSingleton#init() goes here

    # -----

    mw = MainWindow()
    mw.setVisible(True)

    return app.exec_()
