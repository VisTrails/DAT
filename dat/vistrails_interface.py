"""Interface with VisTrails packages.

This is the only module that VisTrails packages need to import. It provides
the classes and methods necessary to define plot types and variable loaders.

You might want to maintain compatibility with VisTrails, like so:
try:
    import dat.vistrails_interface
    from dat.gui import translate # Optional; you might want to use it if you
        # want to internationalize your strings
except ImportError:
    pass # This happens if the package was imported from VisTrails, not from
        # DAT
        # In that case, don't define plots or variable loaders.
else:
    _ = translate('packages.MyPackage') # Create a translator (optional)

    _plots = [
        Plot(...),
    ]

    class MyLoader(dat.vistrails_interface.CustomVariableLoader):
        ...

    _variable_loaders = [
        MyLoader: _("My new loader"),
    ]
"""

import importlib
import inspect
from itertools import izip
import sys
import warnings

from PyQt4 import QtGui

from dat import BaseVariableLoader, PipelineInformation, Plot, Port

from vistrails.core import get_vistrails_application
from vistrails.core.db.action import create_action
from vistrails.core.db.locator import XMLFileLocator
from vistrails.core.modules.module_registry import get_module_registry
from vistrails.core.modules.utils import parse_descriptor_string
from vistrails.core.modules.vistrails_module import Module
from vistrails.packages.spreadsheet.basic_widgets import CellLocation, \
    SpreadsheetCell, SheetReference


__all__ = ['Plot', 'Port', 'Variable',
           'CustomVariableLoader', 'FileVariableLoader']


def resolve_descriptor(param, package_identifier=None):
    """Resolve a type specifier to a ModuleDescriptor.

    This accepts different arguments and turns it into a ModuleDescriptor:
      * a ModuleDescriptor
      * a Module object
      * a descriptor string

    It should be used when accepting type specifiers from third-party code.

    The optional 'package_identifier' parameter gives the context in which to
    resolve module names; it is passed to parse_descriptor_string().
    """
    reg = get_module_registry()

    if isinstance(param, str):
        d_tuple = parse_descriptor_string(param, package_identifier)
        return reg.get_descriptor_by_name(*d_tuple)
    elif isinstance(param, type) and issubclass(param, Module):
        return reg.get_descriptor(param)
    else:
        raise TypeError("add_module() argument must be a Module subclass or "
                        "str object, not '%s'" % type(param))


class ModuleWrapper(object):
    """Object representing a VisTrails module in a DAT variable pipeline.

    This is a wrapper returned by Variable#add_module. It is used by VisTrails
    packages to build a pipeline for a new variable.
    """
    def __init__(self, variable, module_type):
        self._variable = variable
        descriptor = resolve_descriptor(module_type,
                                        self._variable._vt_package_id)
        controller = self._variable._controller
        self._module = controller.create_module_from_descriptor(descriptor)
        self._variable._operations.append(('add', self._module))

    def add_function(self, inputport_name, vt_type, value):
        """Add a function for a port of this module.
        """
        # Check port name
        port = None
        for p in self._module.destinationPorts():
            if p.name == inputport_name:
                port = p
                break

        if port is None:
            raise ValueError("add_function() called for a non-existent input "
                             "port")

        # Check types
        if not isinstance(vt_type, (tuple, list)):
            vt_type = (vt_type,)
        if not isinstance(value, (tuple, list)):
            value = [value]
        if len(vt_type) != len(value):
            raise ValueError("add_function() received different numbers of "
                             "types and values")
        if len(vt_type) != len(port.descriptors()):
            raise ValueError("add_function() called with a different number "
                             "of values from the given input port")
        for t_param, p_descr in izip(vt_type, port.descriptors()):
            t_descr = resolve_descriptor(t_param,
                                         self._variable._vt_package_id)
            if not issubclass(t_descr.module, p_descr.module):
                raise ValueError("add_function() called with incompatible "
                                 "types")

        controller = self._variable._controller
        self._variable._operations.extend(
                controller.update_function_ops(
                        self._module,
                        inputport_name,
                        value))

    def connect_outputport_to(self, outputport_name, other_module, inputport_name):
        """Create a connection between ports of two modules.

        Connects the given output port of this module to the given input port
        of another module.

        The modules must be wrappers for the same Variable.
        """
        if self._variable is not other_module._variable:
            raise ValueError("connect_outputport_to() can only connect "
                             "modules of the same Variable")
        # Might raise vistrails.core.modules.module_registry:MissingPort
        controller = self._variable._controller
        connection = controller.create_connection(
                self._module, outputport_name,
                other_module._module, inputport_name)
        self._variable._operations.append(('add', connection))


class Variable(object):
    """Object used to build a DAT variable.

    This is a wrapper used by VisTrails packages to build a pipeline for a new
    variable. This variable is then stored in the VistrailData.
    Wrapper objects are restored from the Vistrail file easily: they are
    children versions of the version tagged 'dat-vars', and have a tag
    'dat-var-name' where 'name' is the name of that specific DAT variable.
    """

    class VariableInformation(object):
        """Object actually representing a DAT variable.

        Because most of the logic/attribute in Variable become unnecessary once
        the Variable has been materialized in the pipeline, this is the actual
        class of the object we store. It is created by
        Variable#perform_operations().
        """
        def __init__(self, name, controller, type):
            self.name = name
            self._controller = controller
            self.type = type

        def remove(self):
            """Delete the pipeline from the Vistrail.

            This is called by the VistrailData when the Variable is removed.
            """
            controller = self._controller
            version = controller.vistrail.get_version_number(
                    'dat-var-%s' % self.name)
            controller.prune_versions([version])

        def rename(self, new_varname):
            """Change the tag on this version in the Vistrail.

            This is called by the VistrailData when the Variable is renamed.
            """
            controller = self._controller
            version = controller.vistrail.get_version_number(
                    'dat-var-%s' % self.name)
            controller.vistrail.set_tag(version, 'dat-var-%s' % new_varname)

            self.name = new_varname

    @staticmethod
    def _get_variables_root():
        """Create or get the version tagged 'dat-vars'

        This is the base version of all DAT variables. It consists of a single
        OutputPort module with name 'value'.
        """
        controller = get_vistrails_application().get_controller()
        if controller.vistrail.has_tag_str('dat-vars'):
            root_version = controller.vistrail.get_version_number('dat-vars')
        else:
            # Create the 'dat-vars' version
            controller.change_selected_version(0)
            controller.add_module_action
            reg = get_module_registry()
            operations = []

            # Add an OutputPort module
            descriptor = reg.get_descriptor_by_name(
                    'edu.utah.sci.vistrails.basic', 'OutputPort')
            out_mod = controller.create_module_from_descriptor(descriptor)
            operations.append(('add', out_mod))

            # Add a function to this module
            operations.extend(
                    controller.update_function_ops(
                            out_mod,
                            'name',
                            ['value']))

            # Perform the operations
            action = create_action(operations)
            controller.add_new_action(action)
            root_version = controller.perform_action(action)
            # Tag as 'dat-vars'
            controller.vistrail.set_tag(root_version, 'dat-vars')

        controller.change_selected_version(root_version)
        pipeline = controller.current_pipeline
        outmod_id = pipeline.modules.keys()
        assert len(outmod_id) == 1
        outmod_id = outmod_id[0]
        return controller, root_version, outmod_id

    def __init__(self, type=None):
        # Create or get the version tagged 'dat-vars'
        self._controller, self._root_version, self._output_module_id = (
                Variable._get_variables_root())

        # The creation of a Variable is bufferized so as to handle exceptions
        # in VisTrails packages correctly
        # All the operations leading to the materialization of this variable
        # as a pipeline, child of the 'dat-vars' version, are stored in this
        # list and will be added to the Vistrail when perform_operations() is
        # called by the VistrailData
        self._operations = []

        # Get the VisTrails package that's creating this Variable by inspecting
        # the stack
        caller = inspect.currentframe().f_back
        module = inspect.getmodule(caller).__name__
        if module.endswith('.__init__'):
            module = module[:-9]
        if module.endswith('.init'):
            module = module[:-5]
        try:
            pkg = importlib.import_module(module)
            self._vt_package_id = pkg.identifier
        except (ImportError, AttributeError):
            self._vt_package_id = None
        self.type = resolve_descriptor(type, self._vt_package_id)

        self._output_designated = False

    def add_module(self, module_type):
        # Add a new module to the pipeline and return a wrapper
        return ModuleWrapper(self, module_type)

    def select_output_port(self, module, outputport_name):
        """Select the output port of the Variable pipeline.

        The given output port of the given module will be chosen as the output
        port of the Variable. It is this output port that will be connected to
        the Plot subworkflow's input port when creating an actual pipeline.

        This function should be called exactly once when creating a Variable.
        """
        # Connects the output port with the given name of the given wrapped
        # module to the OutputPort module (added at version 'dat-vars')
        if module._variable is not self:
            raise ValueError("select_output_port() designated a module from a "
                             "different Variable")
        elif self._output_designated:
            raise ValueError("select_output_port() was called more than once")

        # Check that the port is compatible to self.type
        try:
            port = module._module.module_descriptor.get_port_spec(
                    outputport_name, 'output')
        except Exception:
            raise ValueError("select_output_port() designated a non-existent "
                             "port")
        # The designated output port has to be a subclass of self.type
        if len(port.descriptors()) != 1:
            raise ValueError("select_output_port() designated a port with "
                             "multiple types")
        if not issubclass(port.descriptors()[0].module, self.type.module):
            raise ValueError("select_output_port() designated a port with an "
                             "incompatible type")

        controller = self._controller

        out_mod = controller.current_pipeline.modules[self._output_module_id]
        connection = controller.create_connection(
                module._module, outputport_name,
                out_mod, 'InternalPipe')
        self._operations.append(('add', connection))

        out_mod
        self._operations.extend(
                controller.update_function_ops(
                        out_mod,
                        'spec',
                        [self.type.sigstring]))

        self._output_designated = True

    def perform_operations(self, name):
        """Materialize this Variable in the Vistrail.

        Create a pipeline tagged as 'dat-var-<varname>' for this Variable,
        children of the 'dat-vars' version.

        This is called by the VistrailData when the Variable is inserted.
        """
        controller = self._controller
        controller.change_selected_version(self._root_version)

        action = create_action(self._operations)
        controller.add_new_action(action)
        self._var_version = controller.perform_action(action)
        controller.vistrail.set_tag(self._var_version,
                                    'dat-var-%s' % name)
        controller.change_selected_version(self._var_version)

        return Variable.VariableInformation(name, controller, self.type)

    @staticmethod
    def read_type(pipeline):
        """Read the type of a Variable from its pipeline.

        The type is obtained from the 'spec' input port of the 'OutputPort'
        module.
        """
        reg = get_module_registry()
        OutputPort = reg.get_module_by_name(
                'edu.utah.sci.vistrails.basic', 'OutputPort')
        outputs = find_modules_by_type(pipeline, [OutputPort])
        if len(outputs) == 1:
            output = outputs[0]
            if get_function(output, 'name') == 'value':
                spec = get_function(output, 'spec')
                return resolve_descriptor(spec)
        return None


class CustomVariableLoader(QtGui.QWidget, BaseVariableLoader):
    """Custom variable loading tab.

    These loaders show up in a tab of their own, allowing to load any kind of
    data from any source.

    It is a widget that the user will use to choose the data he wants to load.
    load() will be called when the user confirms to actually create a Variable
    object.
    reset() is called to reset the widget to its original settings, so that it
    can be reused to load something else.
    get_default_variable_name() should return a sensible variable name for the
    variable that will be loaded; the user can edit it if need be.
    If the default variable name changes because of the user changing its
    selection, default_variable_name_changed() can be called to update it.
    """
    def __init__(self):
        QtGui.QWidget.__init__(self)
        BaseVariableLoader.__init__(self)

    def load(self):
        """Load the variable and return it.

        Implement this in subclasses to load whatever data the user selected as
        a Variable object.
        """
        raise NotImplementedError


class FileVariableLoader(QtGui.QWidget, BaseVariableLoader):
    """A loader that gets a variable from a file.

    Subclasses do not get a tab of their own, but appear on the "File" tab if
    they indicate they are able to load the selected file.
    """
    @classmethod
    def can_load(cls, filename):
        """Indicates whether this loader can read the given file.

        If true, it will be selectable by the user.
        You have to implement this in subclasses.

        Do not actually load the data here, you should only do quick checks
        (like file extension or magic number).
        """
        return False

    def __init__(self):
        """Constructor.

        This constructor receives a 'filename' parameter: the file that we want
        to load. Do not keep the file open thoughout the life of this object,
        it could interfere with other loaders.
        """
        QtGui.QWidget.__init__(self)
        BaseVariableLoader.__init__(self)

    def load(self):
        """Load the variable and return it.

        Implement this in subclasses to do the actual loading of the variable
        from the filename that was given to the constructor, using the desired
        parameters.
        """
        raise NotImplementedError


def get_function(module, function_name):
    """Get the value of a function of a pipeline module.
    """
    for function in module.functions:
        if function.name == function_name:
            if len(function.params) > 0:
                return function.params[0].strValue
    return None


def delete_linked(controller, modules, operations,
                  module_filter=lambda m: True,
                  connection_filter=lambda c: True,
                  depth=sys.maxint):
    """Delete all modules and connections linked to the specified modules.

    module_filter is an optional function called during propagation to modules.

    connection_filter is an optional function called during propagation to
    connections.

    depth_limit is an optional integer limiting the depth of the operation.
    """
    # Build a map of the connections in which each module takes part
    module_connections = dict()
    for connection in controller.current_pipeline.connection_list:
        for mod in (connection.source.moduleId,
                    connection.destination.moduleId):
            try:
                conns = module_connections[mod]
            except KeyError:
                conns = module_connections[mod] = set()
            conns.add(connection)

    visited_connections = set()

    if isinstance(modules, (list, tuple)):
        open_list = modules
    else:
        open_list = [modules]
    to_delete = set(module for module in open_list)

    # At each step
    while depth >= 0 and open_list:
        new_open_list = []
        # For each module considered
        for module in open_list:
            # For each connection it takes part in
            for connection in module_connections.get(module.id, []):
                # If that connection passes the filter
                if (connection not in visited_connections and
                        connection_filter(connection)):
                    # Get the other module
                    if connection.source.moduleId == module.id:
                        other_mod = connection.destination.moduleId
                    else:
                        other_mod = connection.source.moduleId
                    other_mod = controller.current_pipeline.modules[other_mod]
                    if other_mod in to_delete:
                        continue
                    # And if it passes the filter
                    if module_filter(other_mod):
                        # Remove it
                        to_delete.add(other_mod)
                        # And add it to the list
                        new_open_list.append(other_mod)
                visited_connections.add(connection)

        open_list = new_open_list
        depth -= 1

    conn_to_delete = set()
    for module in to_delete:
        conn_to_delete.update(module_connections.get(module.id, []))
    operations.extend(('delete', conn) for conn in conn_to_delete)
    operations.extend(('delete', module) for module in to_delete)


def copy_module(controller, module, operations):
    module = module.do_copy(True, controller.vistrail.idScope, {})
    operations.append(('add', module))
    return module


def find_modules_by_type(pipeline, moduletypes):
    moduletypes = tuple(moduletypes)
    result = []
    for module in pipeline.module_list:
        desc = module.module_descriptor
        if issubclass(desc.module, moduletypes):
            result.append(module)
    return result


def add_variable_subworkflow(controller, varname, plot_ports, operations):
    """ add_variable_subworkflow(controller, var_pipeline, operations: list)
        -> [conn_id: int]

    Copy the variable subworkflow from its own pipeline to the given one, and
    connects it according to the plot_params map.

    It returns the ids of the connections tying this variable to the plot,
    which are used to build the pipeline's var_map.
    """
    var_pipeline = controller.vistrail.getPipeline(
            'dat-var-%s' % varname)

    reg = get_module_registry()
    outputport_desc = reg.get_descriptor_by_name(
            'edu.utah.sci.vistrails.basic', 'OutputPort')

    # Copy every module but the OutputPort
    output_id = None
    var_modules_map = dict() # old_mod_id -> new_module
    for module in var_pipeline.modules.itervalues():
        if (module.module_descriptor is outputport_desc and
                get_function(module, 'name') == 'value'):
            output_id = module.id
        else:
            # We can't just add this module to the new pipeline!
            # We need to create a new one to avoid id collisions
            var_modules_map[module.id] = copy_module(
                    controller, module, operations)

    if output_id is None:
        raise ValueError("add_variable_subworkflow: variable pipeline has no "
                         "'OutputPort' module")

    connection_ids = []
    # Copy every connection except the one to the OutputPort module
    for connection in var_pipeline.connection_list:
        if connection.destination.moduleId == output_id:
            for var_output_mod, var_output_port in plot_ports:
                new_conn = controller.create_connection(
                        var_modules_map[connection.source.moduleId],
                        connection.source.name,
                        var_output_mod,
                        var_output_port)
                operations.append(('add', new_conn))
                connection_ids.append(new_conn.id)
        else:
            new_conn = controller.create_connection(
                    var_modules_map[connection.source.moduleId],
                    connection.source.name,
                    var_modules_map[connection.destination.moduleId],
                    connection.destination.name)
            operations.append(('add', new_conn))

    return connection_ids


def create_pipeline(controller, recipe, cell_info):
    """ create_pipeline(controller, recipe, cell_info: CellInformation)
        -> PipelineInformation

    Create a pipeline in the Vistrail and return its information.
    """
    # Build from the root version
    controller.change_selected_version(0)

    reg = get_module_registry()

    operations = []

    def connect_modules(src_mod, src_port, dest_mod, dest_port):
        new_conn = controller.create_connection(
                src_mod, src_port,
                dest_mod, dest_port)
        operations.append(('add', new_conn))
        return new_conn.id

    inputport_desc = reg.get_descriptor_by_name(
            'edu.utah.sci.vistrails.basic', 'InputPort')

    # Add the plot subworkflow
    locator = XMLFileLocator(recipe.plot.subworkflow)
    vistrail = locator.load()
    version = vistrail.get_latest_version()
    plot_pipeline = vistrail.getPipeline(version)

    # Copy every module but the InputPorts
    plot_modules_map = dict() # old module id -> new module
    for module in plot_pipeline.modules.itervalues():
        if module.module_descriptor is not inputport_desc:
            # We can't just add this module to the new pipeline!
            # We need to create a new one to avoid id collisions
            plot_modules_map[module.id] = copy_module(
                    controller, module, operations)

    def _get_or_create_module(moduleType):
        """Returns or creates a new module of the given type.

        Warns if multiple modules of that type were found.
        """
        modules = find_modules_by_type(plot_pipeline, [moduleType])
        if not modules:
            desc = reg.get_descriptor_from_module(moduleType)
            module = controller.create_module_from_descriptor(desc)
            operations.append(('add', module))
            return module, True
        else:
            # Currently we do not support multiple cell locations in one
            # pipeline but this may be a feature in the future, to have
            # linked visualizations in multiple cells
            if len(modules) > 1:
                warnings.warn("Found multiple %s modules in plot "
                              "subworkflow, only using one." % moduleType)
            return plot_modules_map[modules[0].id], False

    # Connect the CellLocation to the SpreadsheetCell
    cell_modules = find_modules_by_type(plot_pipeline,
                                        [SpreadsheetCell])
    if cell_modules:
        # Add SheetReference and CellLocation modules if the plot
        # subworkflow didn't contain them
        sheet_module, new_sheet = _get_or_create_module(SheetReference)
        location_module, new_location = _get_or_create_module(CellLocation)

        if new_sheet or new_location:
            # Connect the SheetReference to the CellLocation
            connect_modules(
                    sheet_module, 'self',
                    location_module, 'SheetReference')

        if new_location:
            # Connect the CellLocation to the SpreadsheetCell
            cell_module = plot_modules_map[cell_modules[0].id]
            connect_modules(
                    location_module, 'self',
                    cell_module, 'Location')

        if location_module:
            tabwidget = cell_info.tab.tabWidget
            sheetName = tabwidget.tabText(tabwidget.indexOf(cell_info.tab))
            row, col = cell_info.row, cell_info.column
            operations.extend(controller.update_function_ops(
                    sheet_module, 'SheetName', [sheetName]))
            operations.extend(controller.update_function_ops(
                    location_module, 'Row', [row + 1]))
            operations.extend(controller.update_function_ops(
                    location_module, 'Column', [col + 1]))

            if len(cell_modules) > 1:
                warnings.warn("Plot subworkflow '%s' contains more than "
                              "one spreadsheet cell module. Only one "
                              "was connected to a location module." %
                              recipe.plot.name)
    else:
        warnings.warn("Plot subworkflow '%s' does not contain a "
                      "spreadsheet cell module" % recipe.plot.name)

    # Copy the connections and locate the input ports
    plot_params = dict() # param name -> [(module, input port name)]
    for connection in plot_pipeline.connection_list:
        src = plot_pipeline.modules[connection.source.moduleId]
        if src.module_descriptor is inputport_desc:
            param = get_function(src, 'name')
            try:
                ports = plot_params[param]
            except KeyError:
                ports = plot_params[param] = []
            ports.append((
                    plot_modules_map[connection.destination.moduleId],
                    connection.destination.name))
        else:
            connect_modules(
                    plot_modules_map[connection.source.moduleId],
                    connection.source.name,
                    plot_modules_map[connection.destination.moduleId],
                    connection.destination.name)

    # Maps a parameter name to the list of connections tying the variable to
    # modules of the plot
    var_map = dict() # param: str -> [conn_id: int]

    # Add the Variable subworkflows, but 'inline' them
    for param, variable in recipe.variables.iteritems():
        plot_ports = plot_params.get(param, [])

        var_map[param] = add_variable_subworkflow(
                controller,
                variable.name,
                plot_ports,
                operations)

    action = create_action(operations)
    controller.add_new_action(action)
    pipeline_version = controller.perform_action(action)
    controller.vistrail.change_description(
            "Created DAT plot %s" % recipe.plot.name,
            pipeline_version)
    # FIXME : from_root seems to be necessary here, I don't know why
    controller.change_selected_version(pipeline_version, from_root=True)

    # Convert the modules to module ids in the port_map
    port_map = dict()
    for param, portlist in plot_params.iteritems():
        port_map[param] = [(module.id, port) for module, port in portlist]

    return PipelineInformation(pipeline_version, recipe, port_map, var_map)


class UpdateError(ValueError):
    """Error while updating a pipeline.

    This is recoverable by creating a new pipeline from scratch instead. It can
    be caused by the alteration of the data stored in annotations, or by
    changes in the VisTrails package's code.
    """


def update_pipeline(controller, pipelineInfo, new_recipe):
    # Retrieve the pipeline
    controller.change_selected_version(pipelineInfo.version)
    pipeline = controller.current_pipeline
    old_recipe = pipelineInfo.recipe

    # The plots have to be the same
    if old_recipe.plot != new_recipe.plot:
        raise UpdateError("update_pipeline cannot change plot type!")

    operations = []

    var_map = dict()

    # Used to build the description
    added_params = []
    removed_params = []
    updated_params = []

    # Check parameters
    for param in (set(old_recipe.variables.keys()) |
                  set(new_recipe.variables.keys())):
        old_var = old_recipe.variables.get(param)
        new_var = new_recipe.variables.get(param)

        if old_var == new_var:
            try:
                var_map[param] = pipelineInfo.var_map[param]
            except KeyError:
                pass
            continue

        # If the parameter existed (but was removed or changed)
        if old_var is not None:
            connections = [pipeline.connections[c]
                           for c in pipelineInfo.var_map.get(param, [])]
            if not connections:
                raise UpdateError("Couldn't find the connections for "
                                  "parameter '%s' in update data" % param)

            # Remove the variable subworkflow
            modules = [pipeline.modules[c.source.moduleId]
                       for c in connections]
            delete_linked(controller, modules, operations,
                          connection_filter=lambda c: c not in connections)

        # If the parameter exists (but didn't exist or was different)
        if new_var is not None:
            plot_ports = [(pipeline.modules[mod_id], port)
                          for mod_id, port in pipelineInfo.port_map[param]]
            var_map[param] = add_variable_subworkflow(
                    controller,
                    new_var.name,
                    plot_ports,
                    operations)

        if old_var is not None and new_var is not None:
            updated_params.append(param)
        elif old_var is not None:
            removed_params.append(param)
        else: # new_var is not None
            added_params.append(param)

    action = create_action(operations)
    controller.add_new_action(action)
    pipeline_version = controller.perform_action(action)

    if added_params and not removed_params and not updated_params:
        if len(added_params) == 1:
            description = "Added DAT parameter %s" % added_params[0]
        else:
            description = "Added DAT parameters"
    elif removed_params and not added_params and not updated_params:
        if len(removed_params) == 1:
            description = "Removed DAT parameter %s" % removed_params[0]
        else:
            description = "Removed DAT parameters"
    elif updated_params and not added_params and not removed_params:
        if len(updated_params) == 1:
            description = "Updated DAT parameter %s" % updated_params[0]
        else:
            description = "Updated DAT parameters"
    else:
        description = "Changed DAT parameters"
    controller.vistrail.change_description(
            description,
            pipeline_version)

    controller.change_selected_version(pipeline_version)

    return PipelineInformation(pipeline_version, new_recipe,
                               pipelineInfo.port_map, var_map)
