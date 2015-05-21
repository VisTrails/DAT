import logging
import warnings
from PyQt4 import QtCore, QtGui

from dat.gui import translate
from dat.gui import vt_hooks
from dat.gui.window import MainWindow
from dat.global_data import GlobalManager
from dat.vistrail_data import VistrailManager
from dat import vistrails_interface

from vistrails.core.application import set_vistrails_application, \
    get_vistrails_application, VistrailsApplicationInterface
import vistrails.core.requirements
import vistrails.gui.theme
from vistrails.packages.spreadsheet.spreadsheet_cell import CellInformation
from vistrails.packages.spreadsheet.spreadsheet_controller import \
    spreadsheetController
from vistrails.packages.spreadsheet.spreadsheet_tab import \
    StandardWidgetSheetTab


# TODO : maybe this could be pushed back into VisTrails
class NotificationDispatcher(object):
    class UsageWarning(UserWarning):
        """NotificationDispatcher usage warning

        Problems with how notifications are used.
        """

    def __init__(self):
        self._global_notifications = {}
        self._view_notifications = {}
        self._window_notifications = {}

        self.builderWindow = None

    def _get_notification_dict(self, window=None, view=None):
        if view is not None:
            notifications = self._view_notifications.setdefault(view, {})
        elif window is not None:
            notifications = self._window_notifications.setdefault(window, {})
        else:
            notifications = self._global_notifications

        return notifications

    def create_notification(self, notification_id, window=None, view=None):
        """Create a new notification.
        """
        notifications = self._get_notification_dict(window, view)

        if notification_id not in notifications:
            notifications[notification_id] = set()
        else:
            warnings.warn(
                "Notification created twice: %s" % notification_id,
                NotificationDispatcher.UsageWarning,
                stacklevel=2)

    def register_notification(self, notification_id, method,
                              window=None, view=None):
        """Register a function with a notification.
        """
        notifications = self._get_notification_dict(window, view)

        try:
            notifications[notification_id].add(method)
        except KeyError:
            warnings.warn(
                "Registered to non-existing notification %s" % (
                    notification_id),
                NotificationDispatcher.UsageWarning,
                stacklevel=2)
            notifications[notification_id] = set([method])

    def unregister_notification(self, notification_id, method,
                                window=None, view=None):
        """Removes a function from a notification.
        """
        notifications = self._get_notification_dict(window, view)

        try:
            methods = notifications[notification_id]
        except KeyError:
            warnings.warn(
                "Unregistered from non-existing notification %s" % (
                    notification_id),
                NotificationDispatcher.UsageWarning,
                stacklevel=2)
        else:
            try:
                methods.remove(method)
            except KeyError:
                warnings.warn(
                    "Unregistered non-registered method from notification %s" %
                    notification_id,
                    NotificationDispatcher.UsageWarning,
                    stacklevel=2)

    @staticmethod
    def _broadcast_notification(notification_id, methods, args, kwargs):
        for m in methods:
            try:
                m(*args, **kwargs)
            except Exception:
                logging.exception("Got exception while sending notification "
                                  "%s" % notification_id)

    def send_notification(self, notification_id, *args, **kwargs):
        """Send a notification.

        All function that registered with it and that were global or associated
        with the current window or view will be called with the rest of the
        arguments.
        """
        try:
            self._broadcast_notification(
                notification_id,
                self._global_notifications[notification_id],
                args, kwargs)
        except KeyError:
            pass

        if self.builderWindow:
            try:
                self._broadcast_notification(
                    notification_id,
                    self._window_notifications[self.builderWindow]
                                              [notification_id],
                    args, kwargs)
            except KeyError:
                pass

            try:
                view = self.builderWindow.current_view
                self._broadcast_notification(
                    notification_id,
                    self._view_notifications[view][notification_id],
                    args, kwargs)
            except KeyError:
                pass


class Application(QtGui.QApplication, NotificationDispatcher,
                  VistrailsApplicationInterface):
    """Represents the application.

    Replaces VisTrails's application, i.e. gets returned by
    get_vistrails_application().

    Initializes DAT metadata and VisTrails.
    """
    def __init__(self, args):
        QtGui.QApplication.__init__(self, args)
        NotificationDispatcher.__init__(self)
        # There are lots of issues with how the notifications are used
        # Although create_notification() exists, it doesn't seem to be used in
        # every case before register_notification() is called
        warnings.simplefilter('ignore', NotificationDispatcher.UsageWarning)

        VistrailsApplicationInterface.__init__(self)
        self.builderWindow = None
        self._vt_sheet = None
        set_vistrails_application(self)

        vistrails.gui.theme.initializeCurrentTheme()

        VistrailsApplicationInterface.init(self, args=args)
        from vistrails.gui.vistrails_window import QVistrailsWindow
        self.builderWindow = QVistrailsWindow(ui_hooks=vt_hooks.hooks)
        self.builderWindow.closeEvent = lambda e: None

        self.startup.set_package_to_enabled('spreadsheet')
        self.package_manager.initialize_packages()

        self.builderWindow.link_registry()

        # Create a first controller
        view = self.builderWindow.create_first_vistrail()
        controller = view.get_controller()
        assert controller is not None

        # Set our own spreadsheet cell container class
        from dat.gui.cellcontainer import DATCellContainer
        spreadsheetController.setCellContainerClass(DATCellContainer)

        # Discover the plots and variable loaders from packages and register to
        # notifications for packages loaded/unloaded in the future
        GlobalManager.init()

        # Register the VistrailManager with the 'controller_changed'
        # notification
        VistrailManager.init()
        VistrailManager.set_controller(
            controller,
            register=True)

        # Create the main window
        mw = MainWindow()
        mw.setVisible(True)

        # Create the spreadsheet for the first project
        self._controller_changed(controller, new=True)

        # Create a spreadsheet and execute the visualizations when a new
        # controller is selected
        self.register_notification(
            'dat_controller_changed',
            self._controller_changed)

        # Change the current controller when another sheet is selected
        self.register_notification(
            'spreadsheet_sheet_changed',
            self._sheet_changed)

    def _controller_changed(self, controller, new=False):
        if controller is not None:
            QtCore.QMetaObject.invokeMethod(
                self,
                '_controller_changed_deferred',
                QtCore.Qt.QueuedConnection,
                QtCore.Q_ARG(object, controller),
                QtCore.Q_ARG(bool, new))
        # We defer this signal because we need all VisTrails components to
        # notice that the controller changed before we execute something, else
        # components might receive the 'set_pipeline' signal before
        # 'set_controller'

    @QtCore.pyqtSlot(object, bool)
    def _controller_changed_deferred(self, controller, new):
        vistraildata = VistrailManager(controller)
        if vistraildata is None:
            # Non-DAT controller here: create a sheet for it, so that we don't
            # interfere with DAT
            sh_window = spreadsheetController.findSpreadsheetWindow(
                create=False)
            if sh_window is not None:
                tab_controller = sh_window.tabController
                if self._vt_sheet is None:
                    self._vt_sheet = StandardWidgetSheetTab(
                        tab_controller,
                        2, 3)
                    tab_controller.addTabWidget(
                        self._vt_sheet,
                        "VisTrails Sheet")
                    VistrailManager.set_sheet_immortal(self._vt_sheet, True)

                tab_controller.setCurrentWidget(self._vt_sheet)
                return

        # Get the spreadsheets for this project
        spreadsheet_tabs = vistraildata.spreadsheet_tabs

        if new:
            # Execute the pipelines
            for cellInfo, pipeline in vistraildata.all_cells:
                tab = cellInfo.tab
                error = vistrails_interface.try_execute(
                    controller,
                    pipeline)
                if error is not None:
                    from dat.gui.cellcontainer import DATCellContainer
                    tab.setCellWidget(
                        cellInfo.row,
                        cellInfo.column,
                        DATCellContainer(
                            cellInfo=CellInformation(
                                tab,
                                cellInfo.row,
                                cellInfo.column),
                            error=error))

        # Make one of these tabs current
        sh_window = spreadsheetController.findSpreadsheetWindow(
            create=False)
        if sh_window is not None:
            tab = sh_window.tabController.currentWidget()
            if tab not in spreadsheet_tabs.values():
                tab_controller = sh_window.tabController
                tab = next(spreadsheet_tabs.itervalues())
                tabidx = tab_controller.indexOf(tab)
                tab_controller.setCurrentIndex(tabidx)

    def _sheet_changed(self, tab):
        vistraildata = VistrailManager.from_spreadsheet_tab(tab)
        if vistraildata is not None:
            self.builderWindow.ensureController(vistraildata.controller)

    def try_quit(self):
        return self.builderWindow.quit()

    # Various getters required by VisTrails's code...

    def is_running(self):
        return True

    def is_running_gui(self):
        return True

    def get_current_controller(self):
        return self.builderWindow.get_current_controller()
    get_controller = get_current_controller

    def get_vistrail(self):
        controller = self.get_controller()
        return controller and controller.vistrail

    def showBuilderWindow(self):
        QtGui.qApp.setActiveWindow(self.builderWindow)
        self.builderWindow.activateWindow()
        self.builderWindow.show()
        self.builderWindow.raise_()

    def add_vistrail(self, *objs):
        return self.builderWindow.add_vistrail(*objs)

    def remove_vistrail(self, locator):
        self.builderWindow.remove_vistrail(locator)

    def ensure_vistrail(self, locator):
        view = self.builderWindow.ensureVistrail(locator)
        if view is not None:
            return view.controller
        return None

    def select_version(self, version):
        return self.builderWindow.select_version(version)

    def update_locator(self, old_locator, new_locator):
        pass


def start(args=[]):
    """Starts the DAT.

    Creates an application and a window and enters Qt's main loop.
    """
    try:
        app = Application(args)
    except vistrails.core.requirements.MissingRequirement, e:
        _ = translate('dat.application')
        QtGui.QMessageBox.critical(
            None,
            _("Missing requirement"),
            _("VisTrails reports that a requirement is missing.\n"
              "This application can't continue without {required}.")
            .format(required=e.requirement))
        return 1

    return app.exec_()


def stop():
    """Stops the application and cleans up.
    """
    app = get_vistrails_application()
    app.finishSession()
    app.save_configuration()
    app.destroy()
