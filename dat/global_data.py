import warnings

from dat import BaseVariableLoader
from dat.vistrails_interface import resolve_descriptor, Plot, \
    VariableOperation, OperationArgument

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
        self._plots = dict()  # (package_identifier: str, name: str) -> Plot
        self._variable_loaders = set()
        self._variable_operations = set()

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
        # dat_new_operation(loader: VariableOperation)
        app.create_notification('dat_new_operation')
        # dat_removed_operation(loader: VariableOperation)
        app.create_notification('dat_removed_operation')

        app.register_notification("reg_new_package", self.new_package)
        app.register_notification("reg_deleted_package", self.deleted_package)

        # Load the Plots and VariableLoaders from the packages
        registry = get_module_registry()
        for package in registry.package_list:
            self.new_package(package.identifier)

    def _add_plot(self, plot):
        self._plots[(plot.package_identifier, plot.name)] = plot
        get_vistrails_application().send_notification('dat_new_plot', plot)

    def _remove_plot(self, plot):
        del self._plots[(plot.package_identifier, plot.name)]
        get_vistrails_application().send_notification('dat_removed_plot', plot)

    def get_plot(self, package_identifier, plotname):
        """Gets a plot with the given name.

        This is used when building a recipe from a string and when the overlay
        receives a drop (X-Vistrails/DATPlot).
        """
        # Might raise KeyError
        return self._plots[(package_identifier, plotname)]

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

    def _add_operation(self, operation):
        self._variable_operations.add(operation)
        get_vistrails_application().send_notification('dat_new_operation',
                                                      operation)

    def _remove_operation(self, operation):
        self._variable_operations.remove(operation)
        get_vistrails_application().send_notification('dat_removed_operation',
                                                      operation)

    def _get_operations(self):
        return iter(self._variable_operations)
    variable_operations = property(_get_operations)

    def new_package(self, package_identifier, prepend=False):
        """Called when a package is loaded in VisTrails.

        Discovers and registers Plots and VariableLoaders.
        """
        pm = get_package_manager()
        package = pm.get_package(package_identifier)
        if hasattr(package.init_module, '_plots'):
            for plot in package.init_module._plots:
                if not isinstance(plot, Plot):
                    warnings.warn(
                        "Package %s (%s) declares in _plots something "
                        "that is not a plot: %r" % (
                            package_identifier, package.codepath, plot))
                    continue
                plot.package_identifier = package_identifier

                # Resolve the port types
                for port in plot.ports:
                    port.type = resolve_descriptor(port.type,
                                                   package_identifier)

                # Read and check the metadata from the workflow
                try:
                    plot._read_metadata(package_identifier)
                except Exception, e:
                    warnings.warn("In package '%s'\n"
                                  "Couldn't read plot subworkflow for '%s':\n"
                                  "%s" % (package_identifier, plot.name, e))
                else:
                    self._add_plot(plot)
        if hasattr(package.init_module, '_variable_loaders'):
            for loader, name in (package.init_module
                                        ._variable_loaders.iteritems()):
                if not issubclass(loader, BaseVariableLoader):
                    warnings.warn(
                        "Package %s (%s) declares in _variable_loaders "
                        "something that is not a variable loader: %r" % (
                            package_identifier, package.codepath, loader))
                    continue
                loader.package_identifier = package_identifier
                loader.name = name
                self._add_loader(loader)
        if hasattr(package.init_module, '_variable_operations'):
            for operation in package.init_module._variable_operations:
                if not isinstance(operation, VariableOperation):
                    warnings.warn(
                        "Package %s (%s) declares in _operations "
                        "something that is not a variable operation: "
                        "%r" % (package_identifier, package.codepath,
                                operation))
                    continue

                # Resolve the parameter types
                new_args = []
                if operation.usable_in_command:
                    for arg in operation.parameters:
                        new_args.append(OperationArgument(
                            arg.name,
                            tuple(resolve_descriptor(t, package_identifier)
                                  for t in arg.types)))
                    operation.parameters = new_args

                # Resolve the return type
                operation.return_type = resolve_descriptor(
                    operation.return_type,
                    package_identifier)

                operation.package_identifier = package_identifier
                self._add_operation(operation)

    def deleted_package(self, package):
        """Called when a package is unloaded in VisTrails.

        Removes the Plots and VariableLoaders associated with that package from
        the lists.
        """
        for plot in self._plots.values():
            if plot.package_identifier == package.identifier:
                self._remove_plot(plot)

        for loader in list(self._variable_loaders):
            if loader.package_identifier == package.identifier:
                self._remove_loader(loader)

        for operation in list(self._variable_operations):
            if operation.package_identifier == package.identifier:
                self._remove_operation(operation)

GlobalManager = GlobalManager()
