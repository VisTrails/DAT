"""This module contains wrappers used to manipulate modules, variables, ...

Some of this is meant to be used from packages; they are reexported from
:mod:`dat.packages`.
"""

import inspect
from itertools import izip
import os
import warnings

from vistrails.core import get_vistrails_application
from vistrails.core.db.action import create_action
from vistrails.core.db.locator import XMLFileLocator
from vistrails.core.modules.basic_modules import Constant
from vistrails.core.modules.module_registry import get_module_registry
from vistrails.core.modules.sub_module import InputPort
from vistrails.core.vistrail.pipeline import Pipeline
from vistrails.gui.modules.utils import get_widget_class

from dat.vistrails_interface.pipelines import PipelineGenerator
from dat.vistrails_interface.utils import resolve_descriptor, \
    get_upgraded_pipeline, get_function, read_port_specs, find_modules_by_type


class ModuleWrapper(object):
    """Object representing a VisTrails module in a DAT variable pipeline.

    This is a wrapper returned by Variable#add_module. It is used by VisTrails
    packages to build a pipeline for a new variable.
    """
    def __init__(self, variable, module_type):
        self._variable = variable
        descriptor = resolve_descriptor(module_type)
        controller = self._variable._generator.controller
        self._module = controller.create_module_from_descriptor(descriptor)
        self._variable._generator.add_module(self._module)

    def add_function(self, inputport_name, vt_type, value):
        """Add a function for a port of this module.

        vt_type is resolvable to a VisTrails module type (or a list of types).
        value is the value as a string (or a list of strings; the length should
        be the same as vt_type's).
        """
        # Check port name
        try:
            port = self._module.get_port_spec(
                inputport_name, 'input')
        except Exception:
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
            t_descr = resolve_descriptor(t_param)
            if not issubclass(t_descr.module, p_descr.module):
                raise ValueError("add_function() called with incompatible "
                                 "types")

        self._variable._generator.update_function(
            self._module,
            inputport_name,
            value)

    def connect_outputport_to(self, outputport_name,
                              other_module, inputport_name):
        """Create a connection between ports of two modules.

        Connects the given output port of this module to the given input port
        of another module.

        The modules must be wrappers for the same Variable.
        """
        if self._variable is not other_module._variable:
            raise ValueError("connect_outputport_to() can only connect "
                             "modules of the same Variable")
        # Might raise vistrails.core.modules.module_registry:MissingPort
        self._variable._generator.connect_modules(
            self._module, outputport_name,
            other_module._module, inputport_name)


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
        Variable#materialize().
        """
        def __init__(self, name, controller, type, provenance=None):
            self.name = name
            self._controller = controller
            self.type = type
            self.provenance = provenance

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
    def _get_variables_root(controller=None):
        """Create or get the version tagged 'dat-vars'

        This is the base version of all DAT variables. It consists of a single
        OutputPort module with name 'value'.
        """
        if controller is None:
            controller = get_vistrails_application().get_controller()
            assert controller is not None
        if controller.vistrail.has_tag_str('dat-vars'):
            root_version = controller.vistrail.get_version_number('dat-vars')
        else:
            # Create the 'dat-vars' version
            controller.change_selected_version(0)
            reg = get_module_registry()
            operations = []

            # Add an OutputPort module
            descriptor = reg.get_descriptor_by_name(
                'org.vistrails.vistrails.basic', 'OutputPort')
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

    def __init__(self, type, controller=None, generator=None, output=None,
                 provenance=None, materialized=None):
        """Create a new variable.

        type should be resolvable to a VisTrails module type.
        """
        # Create or get the version tagged 'dat-vars'
        controller, self._root_version, self._output_module_id = (
            Variable._get_variables_root(controller))

        self._output_module = None
        self.provenance = provenance

        if generator is None and materialized is None:
            self._generator = PipelineGenerator(controller)
        elif generator is not None:
            self._generator = generator
            if output is not None:
                self._output_module, self._outputport_name = output
        else:
            raise ValueError

        self._materialized = materialized

        self.type = resolve_descriptor(type)

    def add_module(self, module_type):
        """Add a new module to the pipeline and return a wrapper.
        """
        return ModuleWrapper(self, module_type)

    def select_output_port(self, module, outputport_name):
        """Select the output port of the Variable pipeline.

        The given output port of the given module will be chosen as the output
        port of the Variable. It is this output port that will be connected to
        the Plot subworkflow's input port when creating an actual pipeline.

        The selected port should have a type that subclasses the Variable's
        declared type.

        This function should be called exactly once when creating a Variable.
        """
        # Connects the output port with the given name of the given wrapped
        # module to the OutputPort module (added at version 'dat-vars')
        if module._variable is not self:
            raise ValueError("select_output_port() designated a module from a "
                             "different Variable")
        elif self._output_module is not None:
            raise ValueError("select_output_port() was called more than once")

        # Check that the port is compatible to self.type
        try:
            port = module._module.get_port_spec(
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

        self._output_module = module._module
        self._outputport_name = outputport_name

    def materialize(self, name):
        """Materialize this Variable in the Vistrail.

        Create a pipeline tagged as 'dat-var-<varname>' for this Variable,
        children of the 'dat-vars' version.

        This is called by the VistrailData when the Variable is inserted.
        """
        if self._materialized is not None:
            raise ValueError("materialize() called on already materialized "
                             "variable %s (new name: %s)" % (
                                 self._materialized.name, name))

        if self._output_module is None:
            raise ValueError("Invalid Variable: select_output_port() was "
                             "never called")

        controller = self._generator.controller
        controller.change_selected_version(self._root_version)

        out_mod = controller.current_pipeline.modules[self._output_module_id]
        self._generator.connect_modules(
            self._output_module, self._outputport_name,
            out_mod, 'InternalPipe')

        self._generator.update_function(out_mod, 'spec', [self.type.sigstring])

        self._var_version = self._generator.perform_action()
        controller.vistrail.set_tag(self._var_version,
                                    'dat-var-%s' % name)
        controller.change_selected_version(self._var_version)

        variable_info = Variable.VariableInformation(
            name,
            controller,
            self.type,
            self.provenance)
        self._materialized = variable_info
        return variable_info

    @staticmethod
    def read_type(pipeline):
        """Read the type of a Variable from its pipeline.

        The type is obtained from the 'spec' input port of the 'OutputPort'
        module.
        """
        reg = get_module_registry()
        OutputPort = reg.get_module_by_name(
            'org.vistrails.vistrails.basic', 'OutputPort')
        outputs = find_modules_by_type(pipeline, [OutputPort])
        if len(outputs) == 1:
            output = outputs[0]
            if get_function(output, 'name') == 'value':
                spec = get_function(output, 'spec')
                return resolve_descriptor(spec)
        return None

    @staticmethod
    def from_workflow(variable_info, record_materialized=True):
        """Reads back a Variable from a pipeline, given a VariableInformation.
        """
        controller = variable_info._controller
        varname = variable_info.name
        pipeline = get_upgraded_pipeline(
            controller.vistrail,
            'dat-var-%s' % varname)

        generator = PipelineGenerator(controller)
        output = add_variable_subworkflow(generator, pipeline)

        kwargs = dict(
            type=variable_info.type,
            controller=controller,
            generator=generator,
            output=output,
            provenance=variable_info.provenance)
        if record_materialized:
            kwargs['materialized'] = variable_info
        return Variable(**kwargs)


class ArgumentWrapper(object):
    def __init__(self, variable):
        self._variable = variable
        self._copied = False

    def connect_to(self, module, inputport_name):
        generator = module._variable._generator
        if not self._copied:
            # First, we need to copy this pipeline into the new Variable
            generator.append_operations(self._variable._generator.operations)
            self._copied = True
        generator.connect_modules(
            self._variable._output_module,
            self._variable._outputport_name,
            module._module,
            inputport_name)


class Port(object):
    """A simple bean containing informations about one of a plot's port.

    These are optionally passed to Plot's constructor by a VisTrails package,
    else they will be built from the InputPort modules found in the pipeline.

    'accepts' can be either DATA, which means the port should receive a
    variable through drag and drop, or INPUT, which means the port will be
    settable through VisTrails's constant widgets. In the later case, the
    module type should be a constant.
    """
    DATA = 1
    INPUT = 2

    def __init__(self, name, type=None, optional=False, multiple_values=False,
                 accepts=DATA, is_alias=False):
        assert type == Port.INPUT or is_alias is False
        self.name = name
        self.type = type
        self.is_alias = is_alias
        self.optional = optional
        self.multiple_values = multiple_values
        self.accepts = accepts


class DataPort(Port):
    def __init__(self, *args, **kwargs):
        Port.__init__(self, *args, accepts=Port.DATA, **kwargs)


class ConstantPort(Port):
    def __init__(self, *args, **kwargs):
        Port.__init__(self, *args, accepts=Port.INPUT, **kwargs)


class Plot(object):
    def __init__(self, name, **kwargs):
        """A plot descriptor.

        Describes a Plot. These objects should be created by a VisTrails
        package for each Plot it wants to registers with DAT, and added to a
        global '_plots' variable in the 'init' module (for a reloadable
        package).

        name is mandatory and will be displayed to the user.
        description is a text that explains what your Plot is about, and can be
        localized.
        ports should be a list of Port objects describing the input your Plot
        expects.
        subworkflow is the path to the subworkflow that will be used for this
        Plot. In this string, '{package_dir}' will be replaced with the current
        package's path.
        """
        self.name = name
        self.description = kwargs.get('description')

        caller = inspect.currentframe().f_back
        package = os.path.dirname(inspect.getabsfile(caller))

        # Build plot from a subworkflow
        self.subworkflow = kwargs['subworkflow'].format(package_dir=package)
        self.ports = kwargs.get('ports', [])

        # Set the plot config widget, ensuring correct parent class
        from dat.gui.overlays import PlotConfigOverlay, \
            DefaultPlotConfigOverlay
        self.configWidget = kwargs.get('configWidget',
                                       DefaultPlotConfigOverlay)
        if not issubclass(self.configWidget, PlotConfigOverlay):
            warnings.warn("Config widget of plot '%s' does not subclass "
                          "'PlotConfigOverlay'. Using default." % self.name)
            self.configWidget = DefaultPlotConfigOverlay

    def _read_metadata(self, package_identifier):
        """Reads a plot's ports from the subworkflow file

        Finds each InputPort module and gets the parameter name, optional flag
        and type from its 'name', 'optional' and 'spec' input functions.

        If input ports were declared in this Plot, we check that they are
        indeed present and were all listed (either list all of them or none).

        If the module type is a subclass of Constant, we will assume the port
        is to be set via direct input (ConstantPort), else by dragging a
        variable (DataPort).

        We also automatically add aliased input ports of compatible constant
        types as optional ConstantPort's.
        """
        locator = XMLFileLocator(self.subworkflow)
        vistrail = locator.load()
        pipeline = get_upgraded_pipeline(vistrail)

        inputports = find_modules_by_type(pipeline, [InputPort])
        if not inputports:
            raise ValueError("No InputPort module")

        currentports = {port.name: port for port in self.ports}
        seenports = set()
        for port in inputports:
            name = get_function(port, 'name')
            if not name:
                raise ValueError(
                    "Subworkflow of plot '%s' in package '%s' has an "
                    "InputPort with no name" % (
                        self.name, package_identifier))
            if name in seenports:
                raise ValueError(
                    "Subworkflow of plot '%s' in package '%s' has several "
                    "InputPort modules with name '%s'" % (
                        self.name, package_identifier, name))
            spec = get_function(port, 'spec')
            optional = get_function(port, 'optional')
            if optional == 'True':
                optional = True
            elif optional == 'False':
                optional = False
            else:
                optional = None

            try:
                currentport = currentports[name]
            except KeyError:
                # If the package didn't provide any port, it's ok, we can
                # discover them. But if some were present and some were
                # forgotten, emit a warning
                if currentports:
                    warnings.warn(
                        "Declaration of plot '%s' in package '%s' omitted "
                        "port '%s'" % (
                            self.name, package_identifier, name))
                if not spec:
                    warnings.warn(
                        "Subworkflow of plot '%s' in package '%s' has an "
                        "InputPort '%s' with no type; assuming Module" % (
                            self.name, package_identifier, name))
                    spec = 'org.vistrails.vistrails.basic:Module'
                if not optional:
                    optional = False
                type = resolve_descriptor(spec, package_identifier)
                if issubclass(type.module, Constant):
                    currentport = ConstantPort(
                        name=name,
                        type=type,
                        optional=optional)
                else:
                    currentport = DataPort(
                        name=name,
                        type=type,
                        optional=optional)

                self.ports.append(currentport)
            else:
                currentspec = (currentport.type.identifier +
                               ':' +
                               currentport.type.name)
                if ((spec and spec != currentspec) or
                        (optional is not None and
                         optional != currentport.optional)):
                    warnings.warn(
                        "Declaration of port '%s' from plot '%s' in "
                        "package '%s' differs from subworkflow "
                        "contents" % (
                            name, self.name, package_identifier))
                spec = currentspec
                type = resolve_descriptor(currentspec, package_identifier)

            # Get info from the PortSpec
            currentport.default_value = None
            currentport.enumeration = None
            try:
                (default_type, default_value,
                 entry_type, enum_values) = read_port_specs(
                     pipeline,
                     port)
                if default_value is not None:
                    if not issubclass(default_type, type.module):
                        raise ValueError("incompatible type %r" % ((
                                         default_type,
                                         type.module),))
                    elif default_type is type.module:
                        currentport.default_value = default_value
                currentport.entry_type = entry_type
                currentport.enum_values = enum_values
            except ValueError, e:
                raise ValueError(
                    "Error reading specs for port '%s' from plot '%s' of "
                    "package '%s': %s" % (
                        name, self.name, package_identifier, e.args[0]))

            seenports.add(name)

        # Now to add aliased parameters
        for module in pipeline.module_list:
            for function in module.functions:
                port = module.get_port_spec(function.name, 'input')
                problem = None
                if len(port.descriptors()) != 1:
                    problem = (
                        "Aliased parameter '{alias}' on port '{port}' of "
                        "module '{module}' in plot '{plot}' of package "
                        "'{pkg}' has multiple descriptors")
                port_type = port.descriptors()[0]
                if not issubclass(port_type.module, Constant):
                    problem = (
                        "Aliased parameter '{alias}' on port '{port}' of "
                        "module '{module}' in plot '{plot}' of package "
                        "'{pkg}' is not a constant")
                for param in function.parameters:
                    if param.alias:
                        if problem is not None:
                            warnings.warn(problem.format(
                                plot=self.name,
                                pkg=package_identifier,
                                module=module.name,
                                port=function.name,
                                alias=param.alias))
                            continue
                        try:
                            plot_port = currentports[param.alias]
                        except KeyError:
                            plot_port = ConstantPort(
                                name=param.alias,
                                type=port_type,
                                optional=True,
                                is_alias=True)
                            self.ports.append(plot_port)
                        else:
                            plot_port.is_alias = True
                            spec = (plot_port.type.identifier +
                                    ':' +
                                    plot_port.type.name)
                            if spec != port_type.sigstring:
                                warnings.warn(
                                    "Declaration of port '%s' (alias) from "
                                    "plot '%s' in package '%s' differs from "
                                    "subworkflow contents" % (
                                        param.alias, self.name,
                                        package_identifier))
                        psi = port.port_spec_items[0]
                        if (psi.entry_type is not None and
                                psi.entry_type.startswith('enum')):
                            plot_port.entry_type = psi.entry_type
                            plot_port.enum_values = psi.values
                        else:
                            plot_port.entry_type = None
                            plot_port.enum_values = None
                        plot_port.default_value = param.strValue
                        # FIXME : there is no way to not set a value here
                        # Code to get the port's default is below for ref
                        # if port.defaults and port.defaults[0]:
                        #     plot_port.default_value = port.defaults[0]
                        seenports.add(param.alias)

        # If the package declared ports that we didn't see
        missingports = list(set(currentports.keys()) - seenports)
        if currentports and missingports:
            raise ValueError(
                "Declaration of plot '%s' in package '%s' mentions "
                "missing InputPort module '%s'" % (
                    self.name, package_identifier, missingports[0]))

        for port in self.ports:
            if isinstance(port, ConstantPort):
                module = port.type
                port.widget_class = get_widget_class(module)


class VariableOperation(object):
    """An operation descriptor.

    Describes a variable operation. These objects should be created by a
    VisTrails package for each operation it wants to register with DAT, and
    added to a global '_variable_operations' list in the 'init' module (for a
    reloadable package).

    name is mandatory and is what will need to be typed to call the operation.
    It can also be an operator: +, -, *, /
    callback is a function that will be called to construct the new variable
    from the operands.
    args is a tuple; each element is the type (or types) accepted for that
    parameter. For instance, an operation that accepts two arguments, the first
    argument being a String and the second argument either a Float or an
    Integer, use: args=(String, (Float, Integer))
    symmetric means that the function will be called if the arguments are
    backwards; this only works for operations with 2 arguments of different
    types. It is useful for operators such as * and +.
    """
    def __init__(self, name, args=None, return_type=None, callback=None,
                 subworkflow=None, symmetric=False, wizard=None):
        self.name = name
        self.package_identifier = None
        self.parameters = args
        self.return_type = return_type
        self.callback = self.subworkflow = None
        self.usable_in_command = True
        if callback is not None and subworkflow is not None:
            raise ValueError("VariableOperation() got both callback and "
                             "subworkflow parameters")
        elif callback is not None:
            self.callback = callback
        elif subworkflow is not None:
            caller = inspect.currentframe().f_back
            package = os.path.dirname(inspect.getabsfile(caller))
            self.subworkflow = subworkflow.format(package_dir=package)
        elif wizard is None:
            raise ValueError("VariableOperation() got neither callback nor "
                             "subworkflow parameters")
        else:
            self.usable_in_command = False
        if self.usable_in_command:
            if self.parameters is None:
                raise TypeError("missing parameter 'args'")
            if self.return_type is None:
                raise TypeError("missing parameter 'return_type")
        self.symmetric = symmetric
        self.wizard = wizard


class OperationArgument(object):
    """One of the argument of an operation.

    Describes one of the arguments of a VariableOperation. These objects should
    be created by a VisTrails package and passed in a list as the 'args'
    argument of VariableOperation's constructor.

    name is mandatory and is what will be passed to the callback function or
    subworkflow. Note that arguments are passed as keywords, not positional
    arguments.
    types is a VisTrails Module subclass, or a sequence of Module subclasses,
    in which case the argument will accept any of these types.
    """
    def __init__(self, name, types):
        self.name = name
        if isinstance(types, (list, tuple)):
            self.types = tuple(types)
        else:
            self.types = (types,)


def add_variable_subworkflow(generator, variable, plot_ports=None):
    """Add a variable subworkflow to the pipeline.

    Copy the variable subworkflow from its own pipeline to the given one.

    If plot_ports is given, connects the pipeline to the ports in plot_ports,
    and returns the ids of the connections tying this variable to the plot,
    which are used to build the pipeline's conn_map.

    If plot_ports is None, just returns the (module, port_name) of the output
    port.
    """
    if isinstance(variable, Pipeline):
        var_pipeline = variable
    else:
        var_pipeline = get_upgraded_pipeline(
            generator.controller.vistrail,
            'dat-var-%s' % variable)

    reg = get_module_registry()
    outputport_desc = reg.get_descriptor_by_name(
        'org.vistrails.vistrails.basic', 'OutputPort')

    # Copy every module but the OutputPort
    output_id = None
    var_modules_map = dict()  # old_mod_id -> new_module
    for module in var_pipeline.modules.itervalues():
        if (module.module_descriptor is outputport_desc and
                get_function(module, 'name') == 'value'):
            output_id = module.id
        else:
            # We can't just add this module to the new pipeline!
            # We need to create a new one to avoid id collisions
            var_modules_map[module.id] = generator.copy_module(module)

    if output_id is None:
        raise ValueError("add_variable_subworkflow: variable pipeline has no "
                         "'OutputPort' module")

    # Copy every connection except the one to the OutputPort module
    for connection in var_pipeline.connection_list:
        if connection.destination.moduleId != output_id:
            generator.connect_modules(
                var_modules_map[connection.source.moduleId],
                connection.source.name,
                var_modules_map[connection.destination.moduleId],
                connection.destination.name)

    if plot_ports:
        connection_ids = []
        # Connects the port previously connected to the OutputPort to the ports
        # in plot_ports
        for connection in var_pipeline.connection_list:
            if connection.destination.moduleId == output_id:
                for var_output_mod, var_output_port in plot_ports:
                    connection_ids.append(generator.connect_modules(
                        var_modules_map[connection.source.moduleId],
                        connection.source.name,
                        var_output_mod,
                        var_output_port))
        return connection_ids
    else:
        # Just find the output port and return it
        for connection in var_pipeline.connection_list:
            if connection.destination.moduleId == output_id:
                return (var_modules_map[connection.source.moduleId],
                        connection.source.name)
        assert False
