import warnings

from dat import BaseVariableLoader, Plot
from dat.vistrails_interface import resolve_descriptor

from vistrails.core.application import get_vistrails_application
from vistrails.core.modules.module_registry import get_module_registry
from vistrails.core.packagemanager import get_package_manager


class GlobalManager(object):
    """Keeps a list of DAT objects global to the application.

    This singleton allows components throughout the application to access the
    objects that are global to the DAT application: Plots and VariablesLoaders.
    It also emits notifications when these lists are changed.

    It also autodiscovers the Plots and VariableLoaders from VisTrails packages
    when they are loaded, by subscribing to VisTrails's registry notifications.
    """
    def __init__(self):
        self._plots = dict()
        self._variable_loaders = set()

    def init(self):
        """Initial setup of the Manager.

        Discovers plots and variable loaders from packages and registers
        notifications for packages loaded in the future.
        """
        app = get_vistrails_application()

        # dat_new_plot(plot: Plot)
        app.create_notification('dat_new_plot')
        # dat_removed_plot(plot: Plot)
        app.create_notification('dat_removed_plot')
        # dat_new_loader(loader: BaseVariableLoader)
        app.create_notification('dat_new_loader')
        # dat_removed_loader(loader: BaseVariableLoader)
        app.create_notification('dat_removed_loader')

        app.register_notification("reg_new_package", self.new_package)
        app.register_notification("reg_deleted_package", self.deleted_package)

        # Load the Plots and VariableLoaders from the packages
        registry = get_module_registry()
        for package in registry.package_list:
            self.new_package(package.identifier)

    def _add_plot(self, plot):
        self._plots[plot.name] = plot
        get_vistrails_application().send_notification('dat_new_plot', plot)

    def _remove_plot(self, plot):
        del self._plots[plot.name]
        get_vistrails_application().send_notification('dat_removed_plot', plot)

    def get_plot(self, plotname):
        return self._plots[plotname]

    def _get_plots(self):
        return self._plots.itervalues()
    plots = property(_get_plots)

    def _add_loader(self, loader):
        self._variable_loaders.add(loader)
        get_vistrails_application().send_notification('dat_new_loader', loader)

    def _remove_loader(self, loader):
        self._variable_loaders.remove(loader)
        get_vistrails_application().send_notification('dat_removed_loader',
                                                      loader)

    def _get_loaders(self):
        return iter(self._variable_loaders)
    variable_loaders = property(_get_loaders)

    def new_package(self, package_identifier, prepend=False):
        """Called when a package is loaded in VisTrails.

        Discovers and registers Plots and VariableLoaders.
        """
        pm = get_package_manager()
        package = pm.get_package_by_identifier(package_identifier)
        if hasattr(package.init_module, '_plots'):
            for plot in package.init_module._plots:
                if not isinstance(plot, Plot):
                    warnings.warn(
                            "Package %s (%s) declares in _plots something "
                            "that is not a plot: %r" % (
                            package_identifier, package.codepath,
                            plot))
                    continue
                plot.package_identifier = package_identifier
                for port in plot.ports:
                    port.type = resolve_descriptor(port.type,
                                                   package_identifier)
                self._add_plot(plot)
        if hasattr(package.init_module, '_variable_loaders'):
            for loader, name in (package.init_module
                                        ._variable_loaders.iteritems()):
                if not issubclass(loader, BaseVariableLoader):
                    warnings.warn(
                            "Package %s (%s) declares in _variable_loaders "
                            "something that is not a variable loader: %r" % (
                            package_identifier, package.codepath,
                            loader))
                    continue
                loader.package_identifier = package_identifier
                loader.loader_tab_name = name
                self._add_loader(loader)

    def deleted_package(self, package):
        """Called when a package is unloaded in VisTrails.

        Removes the Plots and VariableLoaders associated with that package from
        the lists.
        """
        for plot in self._plots.itervalues():
            if plot.package_identifier == package.identifier:
                self._remove_plot(plot)

        for loader in list(self._variable_loaders):
            if loader.package_identifier == package.identifier:
                self._remove_loader(loader)

GlobalManager = GlobalManager()
