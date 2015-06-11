"""This module contains wrappers used to manipulate modules, variables, ...

Some of this is meant to be used from packages; they are reexported from
:mod:`dat.packages`.
"""

from itertools import izip

from vistrails.core import get_vistrails_application
from vistrails.core.db.action import create_action
from vistrails.core.modules.module_registry import get_module_registry
from vistrails.core.vistrail.pipeline import Pipeline

from dat.vistrails_interface.utils import resolve_descriptor, \
    get_upgraded_pipeline, get_function, find_modules_by_type

from dat.vistrails_interface.pipelines import PipelineGenerator


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
