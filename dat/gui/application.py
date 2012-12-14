import sys
from PyQt4 import QtGui

from dat.gui.window import MainWindow

from vistrails.core.application import (set_vistrails_application,
        VistrailsApplicationInterface)
import vistrails.core.requirements

import vistrails.gui.theme


class Application(VistrailsApplicationInterface):
    def __init__(self):
        VistrailsApplicationInterface.__init__(self)
        self.builderWindow = None
        set_vistrails_application(self)

        vistrails.gui.theme.initializeCurrentTheme()

        VistrailsApplicationInterface.init(self)
        from vistrails.gui.vistrails_window import QVistrailsWindow
        self.builderWindow = QVistrailsWindow()
        self.builderWindow.setVisible(True) # DEBUG : this will be hidden by default
        self.vistrailsStartup.init()

    def is_running(self):
        return True

    def is_running_gui(self):
        return True


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
    Application()

    # -----

    mw = MainWindow()
    mw.setVisible(True)

    return app.exec_()
