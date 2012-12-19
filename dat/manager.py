import warnings

from dat.packages import _BaseVariableLoader, Plot

from vistrails.core.application import get_vistrails_application
from vistrails.core.modules.module_registry import get_module_registry
from vistrails.core.packagemanager import get_package_manager


class Manager(object):
    def __init__(self):
        self._plot_observers = set()
        self._loader_observers = set()

        self._plots = set()
        self._variable_loaders = set()

    def add_plot_observer(self, callbacks):
        """Registers an observer for the plots.

        callbacks is a tuple (plot_added, plot_removed).
        """
        if not isinstance(callbacks, tuple) or not len(callbacks) == 2:
            raise TypeError
        self._plot_observers.add(callbacks)

    def add_loader_observer(self, callbacks):
        """Registers an observer for the variable loaders.

        callbacks is a tuple (loader_added, loader_removed).
        """
        if not isinstance(callbacks, tuple) or not len(callbacks) == 2:
            raise TypeError
        self._loader_observers.add(callbacks)

    def init(self):
        """Initial setup of the Manager.

        Discovers plots and variable loaders from packages and registers
        notifications for packages loaded in the future.
        """
        app = get_vistrails_application()
        app.register_notification("reg_new_package", self.new_package)
        app.register_notification("reg_deleted_package", self.deleted_package)

        registry = get_module_registry()
        for package in registry.package_list:
            self.new_package(package.identifier)

    def _add_plot(self, plot):
        self._plots.add(plot)
        for obs in self._plot_observers:
            obs[0](plot)

    def _remove_plot(self, plot):
        self._plots.remove(plot)
        for obs in self._plot_observers:
            obs[1](plot)

    def _get_plots(self):
        return iter(self._plots)
    plots = property(_get_plots)

    def _add_loader(self, loader):
        self._variable_loaders.add(loader)
        for obs in self._loader_observers:
            obs[0](loader)

    def _remove_loader(self, loader):
        self._variable_loaders.remove(loader)
        for obs in self._loader_observers:
            obs[1](loader)

    def _get_loaders(self):
        return iter(self._variable_loaders)
    variable_loaders = property(_get_loaders)

    def new_package(self, package_identifier, prepend=False):
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
                self._add_plot(plot)
        if hasattr(package.init_module, '_variable_loaders'):
            for loader, name in package.init_module._variable_loaders.iteritems():
                if not issubclass(loader, _BaseVariableLoader):
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
        for plot in list(self._plots):
            if plot.package_identifier == package.identifier:
                self._remove_plot(plot)

        for loader in list(self._variable_loaders):
            if loader.package_identifier == package.identifier:
                self._remove_loader(loader)

    def __call__(self):
        return self

Manager = Manager()
