"""Interface with VisTrails.

This package contains most of the code that deals with VisTrails pipelines.
"""

import inspect
from itertools import chain
import os
import warnings

from PyQt4 import QtCore, QtGui

from dat import BaseVariableLoader, DATRecipe, PipelineInformation, \
    RecipeParameterValue, DEFAULT_VARIABLE_NAME
from dat.gui import translate
from dat.vistrails_interface.pipelines import PipelineGenerator, \
    add_constant_module
from dat.vistrails_interface.utils import get_upgraded_pipeline, \
    get_function, walk_modules, find_modules_by_type
from dat.vistrails_interface.wrappers import Variable, ArgumentWrapper, \
    ConstantPort, add_variable_subworkflow

from vistrails.core import get_vistrails_application
from vistrails.core.db.action import create_action
from vistrails.core.db.locator import XMLFileLocator
from vistrails.core.interpreter.default import get_default_interpreter
from vistrails.core.modules.module_registry import get_module_registry
from vistrails.core.utils import DummyView
from vistrails.core.vistrail.controller import VistrailController
from vistrails.core.vistrail.vistrail import Vistrail
from vistrails.packages.spreadsheet.basic_widgets import CellLocation, \
    SpreadsheetCell, SheetReference


class CancelExecution(RuntimeError):
    pass


def get_variable_value(variable):
    """Get the value of a variable, i.e. the result of its pipeline.

    The 'variable' can either be a Variable, from which a temporary pipeline
    will be built, or a VariableInformation, representing an existing pipeline.
    """
    def pipeline_from_info(variableinfo):
        controller = variableinfo._controller
        version = controller.vistrail.get_version_number(
            'dat-var-%s' % variable.name)
        return controller.vistrail.getPipeline(version), version

    def pipeline_from_generator(variable_gen):
        # Get the original OutputPort module
        orig_controller = variable_gen._generator.controller
        base_pipeline = orig_controller.vistrail.getPipeline('dat-vars')
        if len(base_pipeline.module_list) != 1:
            raise ValueError("dat-vars version is invalid")
        output_port = base_pipeline.module_list[0]

        controller = VistrailController(Vistrail())
        # OutputPort
        operations = [('add', output_port)]
        # Rest of the pipeline
        operations += variable_gen._generator.operations
        # Connection
        connection = controller.create_connection(
            variable_gen._output_module,
            variable_gen._outputport_name,
            output_port,
            'InternalPipe')
        operations.append(('add', connection))
        # Materialize this
        action = create_action(operations)
        controller.add_new_action(action)
        version = controller.perform_action(action)
        controller.change_selected_version(version)
        assert version == controller.current_version == 1
        return controller.current_pipeline, 1

    # Obtain 'pipeline' and 'version' from 'variable'
    if isinstance(variable, Variable.VariableInformation):
        # Pipeline already exists
        pipeline, version = pipeline_from_info(variable)
    elif isinstance(variable, Variable):
        if variable._materialized is not None:
            # Pipeline already exists
            pipeline, version = pipeline_from_info(variable._materialized)
        else:
            # Pipeline doesn't exist
            # We need to make one from the operations
            pipeline, version = pipeline_from_generator(variable)
    else:
        raise TypeError

    # Setup the interpreter for execution
    interpreter = get_default_interpreter()
    interpreter.clean_non_cacheable_modules()
    interpreter.parent_execs = [None]
    res = interpreter.setup_pipeline(pipeline)
    if len(res[5]) > 0:
        raise ValueError("Variable pipeline has errors:\n%s" %
                         '\n'.join(me.msg for me in res[5].itervalues()))
    tmp_id_to_module_map = res[0]

    # Execute
    res = interpreter.execute_pipeline(
        pipeline,
        res[0],  # tmp_id_to_module_map
        res[1],  # persistent_to_tmp_id_map
        current_version=version,
        reason="getting variable value")
    if len(res[2]) > 0:
        raise ValueError("Error while executing variable pipeline:\n%s" %
                         '\n'.join('%s: %s' % (me.module.__class__.__name__,
                                               me.msg)
                                   for me in res[2].itervalues()))
    if len(res[4]) > 0:
        # extract messages and previous ModuleSuspended exceptions
        raise ValueError("Module got suspended while executing variable "
                         "pipeline:\n%s" %
                         '\n'.join(msg for msg in res[4].itervalues()))

    # Get the result
    outputport_desc = get_module_registry().get_descriptor_by_name(
        'org.vistrails.vistrails.basic', 'OutputPort')
    for module in pipeline.module_list:
        if module.module_descriptor is outputport_desc:
            if get_function(module, 'name') == 'value':
                module_obj = tmp_id_to_module_map[module.id]
                result = module_obj.get_output('ExternalPipe')
                break
    else:
        result = None

    interpreter.finalize_pipeline(pipeline, *res[:-1])
    interpreter.parent_execs = [None]
    return result


def call_operation_callback(op, callback, args):
    """Call a VariableOperation callback to build a new Variable.

    op is the requested operation.
    callback is the VisTrails package's function that is wrapped here.
    args is a list of Variable that are the arguments of the operation; they
    need to be wrapped as the package is not supposed to manipulate these
    directly.
    """
    kwargs = dict()
    for i in xrange(len(args)):
        kwargs[op.parameters[i].name] = ArgumentWrapper(args[i])
    result = callback(**kwargs)
    for argname, arg in kwargs.iteritems():
        if not arg._copied:
            warnings.warn("In operation %r, argument %r was not used" % (
                          op.name, argname))
    return result


def apply_operation_subworkflow(controller, op, subworkflow, args):
    """Load an operation subworkflow from a file to build a new Variable.

    op is the requested operation.
    subworkflow is the filename of an XML file.
    args is a list of Variable that are the arguments of the operation; they
    will be connected in place of the operation subworkflow's InputPort
    modules.
    """
    reg = get_module_registry()
    inputport_desc = reg.get_descriptor_by_name(
        'org.vistrails.vistrails.basic', 'InputPort')
    outputport_desc = reg.get_descriptor_by_name(
        'org.vistrails.vistrails.basic', 'OutputPort')

    generator = PipelineGenerator(controller)

    # Add the operation subworkflow
    locator = XMLFileLocator(subworkflow)
    vistrail = locator.load()
    operation_pipeline = get_upgraded_pipeline(vistrail)

    # Copy every module but the InputPorts and the OutputPort
    operation_modules_map = dict()  # old module id -> new module
    for module in operation_pipeline.modules.itervalues():
        if module.module_descriptor not in (inputport_desc, outputport_desc):
            operation_modules_map[module.id] = generator.copy_module(module)

    # Copy the connections and locate the input ports and the output port
    operation_params = dict()  # param name -> [(module, input port name)]
    output = None  # (module, port name)
    for connection in operation_pipeline.connection_list:
        src = operation_pipeline.modules[connection.source.moduleId]
        dest = operation_pipeline.modules[connection.destination.moduleId]
        if src.module_descriptor is inputport_desc:
            param = get_function(src, 'name')
            ports = operation_params.setdefault(param, [])
            ports.append((
                operation_modules_map[connection.destination.moduleId],
                connection.destination.name))
        elif dest.module_descriptor is outputport_desc:
            output = (operation_modules_map[connection.source.moduleId],
                      connection.source.name)
        else:
            generator.connect_modules(
                operation_modules_map[connection.source.moduleId],
                connection.source.name,
                operation_modules_map[connection.destination.moduleId],
                connection.destination.name)

    # Add the parameter subworkflows
    for i in xrange(len(args)):
        generator.append_operations(args[i]._generator.operations)
        o_mod = args[i]._output_module
        o_port = args[i]._outputport_name
        for i_mod, i_port in operation_params.get(op.parameters[i].name, []):
            generator.connect_modules(
                o_mod, o_port,
                i_mod, i_port)

    return Variable(
        type=op.return_type,
        controller=controller,
        generator=generator,
        output=output)


class SimpleVariableLoaderMixin(object):
    def __init__(self, filename=None):
        super(SimpleVariableLoaderMixin, self).__init__()

        if isinstance(self, CustomVariableLoader) and filename is not None:
            raise TypeError
        elif isinstance(self, FileVariableLoader):
            if filename is None:
                raise TypeError
            self.__filename = filename

        self.__parameters = dict()
        if not self._simple_parameters:
            _ = translate(SimpleVariableLoaderMixin)
            layout = QtGui.QVBoxLayout()
            layout.addWidget(QtGui.QLabel(_("This loader has no parameters.")))
            self.setLayout(layout)
            return

        layout = QtGui.QFormLayout()
        for name, opts in self._simple_parameters:
            # Unpack options
            if not isinstance(opts, (tuple, list)):
                ptype, pdef, pdesc = opts, None, None
            else:
                ptype, pdef, pdesc = opts + (None,) * (3 - len(opts))

            # Widgets
            if issubclass(ptype, basestring):
                widget = QtGui.QLineEdit()
                if pdef is not None:
                    widget.setText(pdef)
                    resetter = lambda: widget.setText(pdef)
                else:
                    resetter = lambda: widget.setText('')
                getter = lambda: widget.text()
            elif ptype is int:
                widget = QtGui.QSpinBox()
                if pdef is None:
                    resetter = lambda: widget.setValue(0)
                elif isinstance(pdef, (tuple, list)):
                    if len(pdef) != 3:
                        raise ValueError
                    widget.setRange(pdef[1], pdef[2])
                    widget.setValue(pdef[0])
                    resetter = lambda: widget.setValue(pdef[0])
                else:
                    widget.setValue(pdef)
                    resetter = lambda: widget.setValue(pdef)
                getter = lambda: widget.value()
            elif ptype is bool:
                widget = QtGui.QCheckBox()
                if pdef:
                    widget.setChecked(True)
                    resetter = lambda: widget.setChecked(True)
                else:
                    resetter = lambda: widget.setChecked(False)
                getter = lambda: widget.isChecked()
            else:
                raise ValueError("No simple widget type for parameter "
                                 "type %r" % (ptype,))

            # Store widget in layout and (widget,  getter) in a dict
            if pdesc is not None:
                layout.addRow(pdesc, widget)
            else:
                layout.addRow(name, widget)
            self.__parameters[name] = (getter, resetter)

        self.setLayout(layout)

    def reset(self):
        for name, (getter, resetter) in self.__parameters.iteritems():
            resetter()

    @classmethod
    def can_load(cls, filename):
        if cls._simple_extension is not None:
            return filename.lower().endswith(cls._simple_extension)
        else:
            return True

    def load(self):
        if isinstance(self, CustomVariableLoader):
            return self._simple_load()
        else:  # isinstance(self, FileVariableLoader):
            return self._simple_load(self.__filename)

    def get_default_variable_name(self):
        if (isinstance(self, FileVariableLoader) and
                self._simple_get_varname is not None):
            return self._simple_get_varname(self.__filename)
        return self._simple_default_varname

    def get_parameter(self, name):
        getter, resetter = self.__parameters[name]
        return getter()


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

    @staticmethod
    def simple(parameters=dict(), default_varname=DEFAULT_VARIABLE_NAME,
               load=None):
        """Make a variable loader very simply.

        This function can be used to create a CustomVariableLoader very simply,
        without having to create a full class or to create a Qt widget.
        Instead, 'parameters' are defined; the correct widget type will be
        automatically created and their values will be accessible with
        get_parameter() from the load callback.

        parameters is a list of tuples with the form:
            'param name', (type, default, description)
        It should be thought of as a dict, but ordered, thus list of key-value
        pairs.
        Example:
            [
            ('url', str),
            ('user', (str, 'admin')),
            ('password', (str, '', "Password: (birthdate by default)"));
            ]
        load is the callback used to build the variable, it will be given the
        filename as only argument.
        """
        return type(
            'CustomVariableLoader.simple_',
            (SimpleVariableLoaderMixin, CustomVariableLoader),
            dict(_simple_parameters=parameters,
                 _simple_default_varname=default_varname,
                 _simple_load=load))


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

    @staticmethod
    def simple(parameters=dict(), default_varname=DEFAULT_VARIABLE_NAME,
               extension=None, load=None, get_varname=None):
        """Make a variable loader very simply.

        This function can be used to create a CustomVariableLoader very simply,
        without having to create a full class or to create a Qt widget.
        Instead, 'parameters' are defined; the correct widget type will be
        automatically created and their values will be accessible with
        get_parameter() from the load callback.

        parameters is a list of tuples with the form:
            'param name', (type, default, description)
        It should be thought of as a dict, but ordered, thus list of key-value
        pairs.
        Example:
            [
            ('url', str),
            ('user', (str, 'admin')),
            ('password', (str, '', "Password: (birthdate by default)"));
            ]
        extension is the file extension of the files that will be accepted; if
        None, every file is accepted.
        load is the callback used to build the variable, it will be given the
        filename as only argument.
        get_varname is an optional callback used to get the new variable's
        default name, it will be given the filename as only argument.
        """
        return type(
            'CustomVariableLoader.simple_',
            (SimpleVariableLoaderMixin, FileVariableLoader),
            dict(_simple_parameters=parameters,
                 _simple_default_varname=default_varname,
                 _simple_extension=extension,
                 _simple_load=load,
                 _simple_get_varname=staticmethod(get_varname)))


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


def get_pipeline_location(controller, pipelineInfo):
    pipeline = get_upgraded_pipeline(controller.vistrail, pipelineInfo.version)

    location_modules = find_modules_by_type(pipeline, [CellLocation])
    if len(location_modules) != 1:
        raise ValueError
    loc = location_modules[0]
    row = int(get_function(loc, 'Row')) - 1
    col = int(get_function(loc, 'Column')) - 1

    sheetref_modules = find_modules_by_type(pipeline, [SheetReference])
    if len(sheetref_modules) != 1:
        raise ValueError
    ref = sheetref_modules[0]
    for connection in pipeline.connection_list:
        src = pipeline.modules[connection.source.moduleId]
        if connection.destination.moduleId == ref.id and src.is_vistrail_var():
            var_uuid = src.get_vistrail_var()
            sheetname_var = controller.get_vistrail_variable_by_uuid(var_uuid)
            return row, col, sheetname_var
    raise ValueError


def get_plot_modules(pipelineInfo, pipeline):
    """Gets all the modules from the plot subpipeline in a given pipeline.
    """
    # To get all the modules of the plot:
    # We start from the input ports (modules in the port_map) and we follow
    # edges, without traversing one of the connections from the conn_map
    ignore_edges = set(conn_id
                       for param in pipelineInfo.conn_map.itervalues()
                       for var in param
                       for conn_id in var)  # set([conn_id: int])
    init_modules = set(pipeline.modules[mod_id]
                       for lp in pipelineInfo.port_map.itervalues()
                       for mod_id, port_name in lp)
    modules, conns = walk_modules(
        pipeline,
        init_modules,
        connection_filter=lambda c: c.id not in ignore_edges)
    modules = filter(lambda m: m.module_descriptor.module is not CellLocation,
                     modules)
    return modules


def add_variable_subworkflow_typecast(generator, variable, plot_ports,
                                      expected_type, typecast):
    if issubclass(variable.type.module, expected_type.module):
        return (add_variable_subworkflow(generator,
                                         variable.name,
                                         plot_ports),
                RecipeParameterValue(variable=variable))
    else:
        # Load the variable from the workflow
        var_pipeline = Variable.from_workflow(variable)

        # Apply the operation
        var_pipeline, typecast_operation = typecast(
            generator.controller, var_pipeline,
            variable.type, expected_type)

        generator.append_operations(var_pipeline._generator.operations)
        if plot_ports:
            connection_ids = []
            for var_output_mod, var_output_port in plot_ports:
                connection_ids.append(generator.connect_modules(
                    var_pipeline._output_module,
                    var_pipeline._outputport_name,
                    var_output_mod,
                    var_output_port))
            return connection_ids, RecipeParameterValue(
                variable=variable,
                typecast=typecast_operation.name)
        else:
            return (var_pipeline._output_module, var_pipeline._outputport_name)


def create_pipeline(controller, recipe, row, column, var_sheetname,
                    typecast=None):
    """Create a pipeline from a recipe and return its information.
    """
    # Build from the root version
    controller.change_selected_version(0)

    reg = get_module_registry()

    generator = PipelineGenerator(controller)

    inputport_desc = reg.get_descriptor_by_name(
        'org.vistrails.vistrails.basic', 'InputPort')

    # Add the plot subworkflow
    locator = XMLFileLocator(recipe.plot.subworkflow)
    vistrail = locator.load()
    plot_pipeline = get_upgraded_pipeline(vistrail)

    connected_to_inputport = set(
        c.source.moduleId
        for c in plot_pipeline.connection_list
        if plot_pipeline.modules[
            c.destination.moduleId
        ].module_descriptor is inputport_desc)

    # Copy every module but the InputPorts and up
    plot_modules_map = dict()  # old module id -> new module
    for module in plot_pipeline.modules.itervalues():
        if (module.module_descriptor is not inputport_desc and
                module.id not in connected_to_inputport):
            plot_modules_map[module.id] = generator.copy_module(module)

    del connected_to_inputport

    def _get_or_create_module(moduleType):
        """Returns or creates a new module of the given type.

        Warns if multiple modules of that type were found.
        """
        modules = find_modules_by_type(plot_pipeline, [moduleType])
        if not modules:
            desc = reg.get_descriptor_from_module(moduleType)
            module = controller.create_module_from_descriptor(desc)
            generator.add_module(module)
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
        cell_module = plot_modules_map[cell_modules[0].id]

        # Add a CellLocation module if the plot subworkflow didn't contain one
        location_module, new_location = _get_or_create_module(CellLocation)

        if new_location:
            # Connect the CellLocation to the SpreadsheetCell
            generator.connect_modules(
                location_module, 'value',
                cell_module, 'Location')

        generator.update_function(
            location_module, 'Row', [str(row + 1)])
        generator.update_function(
            location_module, 'Column', [str(column + 1)])

        if len(cell_modules) > 1:
            warnings.warn("Plot subworkflow '%s' contains more than "
                          "one spreadsheet cell module. Only one "
                          "was connected to a location module." %
                          recipe.plot.name)

        # Add a SheetReference module
        sheetref_module, new_sheetref = _get_or_create_module(SheetReference)

        if new_sheetref or new_location:
            # Connection the SheetReference to the CellLocation
            generator.connect_modules(
                sheetref_module, 'value',
                location_module, 'SheetReference')

        generator.connect_var(
            var_sheetname,
            sheetref_module,
            'SheetName')
    else:
        warnings.warn("Plot subworkflow '%s' does not contain a "
                      "spreadsheet cell module" % recipe.plot.name)

    # TODO : use walk_modules() to find all  modules above an InputPort's
    # 'Default' port and ignore them in the following loop

    # Copy the connections and locate the input ports
    plot_params = dict()  # param name -> [(module, input port name)]
    for connection in plot_pipeline.connection_list:
        src = plot_pipeline.modules[connection.source.moduleId]
        dest = plot_pipeline.modules[connection.destination.moduleId]
        if dest.module_descriptor is inputport_desc:
            continue
        elif src.module_descriptor is inputport_desc:
            param = get_function(src, 'name')
            ports = plot_params.setdefault(param, [])
            ports.append((
                plot_modules_map[connection.destination.moduleId],
                connection.destination.name))
        else:
            generator.connect_modules(
                plot_modules_map[connection.source.moduleId],
                connection.source.name,
                plot_modules_map[connection.destination.moduleId],
                connection.destination.name)

    # Find the constant ports declared with aliases
    aliases = {port.name: port for port in recipe.plot.ports if port.is_alias}
    for module in plot_pipeline.module_list:
        for function in module.functions:
            remove = False
            for param in function.parameters:
                if param.alias in aliases:
                    plot_params[param.alias] = [(
                        plot_modules_map[module.id],
                        function.name)]
                    remove = True

            if remove:
                # Remove the function from the generated pipeline
                generator.update_function(
                    plot_modules_map[module.id],
                    function.name,
                    None)
    del aliases

    # Adds default values for unset constants
    parameters_incl_defaults = dict(recipe.parameters)
    for port in recipe.plot.ports:
        if (isinstance(port, ConstantPort) and
                port.default_value is not None and
                port.name not in recipe.parameters):
            parameters_incl_defaults[port.name] = [RecipeParameterValue(
                constant=port.default_value)]

    # Maps a port name to the list of parameters
    # for each parameter, we have a list of connections tying it to modules of
    # the plot
    conn_map = dict()  # param: str -> [[conn_id: int]]

    name_to_port = {port.name: port for port in recipe.plot.ports}
    actual_parameters = {}
    for port_name, parameters in parameters_incl_defaults.iteritems():
        plot_ports = plot_params.get(port_name, [])
        p_conns = conn_map[port_name] = []
        actual_values = []
        for parameter in parameters:
            if parameter.type == RecipeParameterValue.VARIABLE:
                conns, actual_param = add_variable_subworkflow_typecast(
                    generator,
                    parameter.variable,
                    plot_ports,
                    name_to_port[port_name].type,
                    typecast=typecast)
                p_conns.append(conns)
                actual_values.append(actual_param)
            else:  # parameter.type == RecipeParameterValue.CONSTANT
                desc = name_to_port[port_name].type
                p_conns.append(add_constant_module(
                    generator,
                    desc,
                    parameter.constant,
                    plot_ports))
                actual_values.append(parameter)
        actual_parameters[port_name] = actual_values
    del name_to_port

    pipeline_version = generator.perform_action()
    controller.vistrail.change_description(
        "Created DAT plot %s" % recipe.plot.name,
        pipeline_version)
    # FIXME : from_root seems to be necessary here, I don't know why
    controller.change_selected_version(pipeline_version, from_root=True)

    # Convert the modules to module ids in the port_map
    port_map = dict()
    for param, portlist in plot_params.iteritems():
        port_map[param] = [(module.id, port) for module, port in portlist]

    return PipelineInformation(
        pipeline_version,
        DATRecipe(recipe.plot, actual_parameters),
        conn_map, port_map)


class UpdateError(ValueError):
    """Error while updating a pipeline.

    This is recoverable by creating a new pipeline from scratch instead. It can
    be caused by the alteration of the data stored in annotations, or by
    changes in the VisTrails package's code.
    """


def update_pipeline(controller, pipelineInfo, new_recipe, typecast=None):
    """Update a pipeline to a new recipe.

    This takes a similar pipeline and turns it into the new recipe by adding/
    removing/replacing the variable subworkflows.

    It will raise UpdateError if it can't be done; in this case
    create_pipeline() should be considered.
    """
    # Retrieve the pipeline
    controller.change_selected_version(pipelineInfo.version)
    pipeline = controller.current_pipeline
    old_recipe = pipelineInfo.recipe

    # The plots have to be the same
    if old_recipe.plot != new_recipe.plot:
        raise UpdateError("update_pipeline cannot change plot type!")

    generator = PipelineGenerator(controller)

    conn_map = dict()

    # Used to build the description
    added_params = []
    removed_params = []

    name_to_port = {port.name: port for port in new_recipe.plot.ports}
    actual_parameters = {}
    for port_name in (set(old_recipe.parameters.iterkeys()) |
                      set(new_recipe.parameters.iterkeys())):
        # param -> [[conn_id]]
        old_params = dict()
        for i, param in enumerate(old_recipe.parameters.get(port_name, [])):
            conns = old_params.setdefault(param, [])
            conns.append(list(pipelineInfo.conn_map[port_name][i]))
        new_params = list(new_recipe.parameters.get(port_name, []))
        conn_lists = conn_map.setdefault(port_name, [])

        # Loop on new parameters
        actual_values = []
        for param in new_params:
            # Remove one from old_params
            old = old_params.get(param)
            if old:
                old_conns = old.pop(0)
                if not old:
                    del old_params[param]

                conn_lists.append(old_conns)
                actual_values.append(param)
                continue

            # Can't remove, meaning that there is more of this param than there
            # was before
            # Add this param on this port
            plot_ports = [(pipeline.modules[mod_id], port)
                          for mod_id, port in (
                              pipelineInfo.port_map[port_name])]
            if param.type == RecipeParameterValue.VARIABLE:
                conns, actual_param = add_variable_subworkflow_typecast(
                    generator,
                    param.variable,
                    plot_ports,
                    name_to_port[port_name].type,
                    typecast=typecast)
                conn_lists.append(conns)
                actual_values.append(actual_param)
            else:  # param.type == RecipeParameterValue.CONSTANT:
                desc = name_to_port[port_name].type
                conn_lists.append(add_constant_module(
                    generator,
                    desc,
                    param.constant,
                    plot_ports))
                actual_values.append(param)

            added_params.append(port_name)

        # Now loop on the remaining old parameters
        # If they haven't been removed by the previous loop, that means that
        # there were more of them in the old recipe
        for conn_lists in old_params.itervalues():
            for connections in conn_lists:
                # Remove the variable subworkflow
                modules = set(
                    pipeline.modules[pipeline.connections[c].source.moduleId]
                    for c in connections)
                generator.delete_linked(
                    modules,
                    connection_filter=lambda c: c.id not in connections)

                removed_params.append(port_name)

        actual_parameters[port_name] = actual_values

    # We didn't find anything to change
    if not (added_params or removed_params):
        return pipelineInfo

    pipeline_version = generator.perform_action()

    controller.vistrail.change_description(
        describe_dat_update(added_params, removed_params),
        pipeline_version)

    controller.change_selected_version(pipeline_version, from_root=True)

    return PipelineInformation(
        pipeline_version,
        DATRecipe(new_recipe.plot, actual_parameters),
        conn_map, pipelineInfo.port_map)


def describe_dat_update(added_params, removed_params):
    """Makes a readable description from a DAT recipe change.
    """
    # We only added parameters
    if added_params and not removed_params:
        # We added one
        if len(added_params) == 1:
            return "Added DAT parameter to %s" % added_params[0]
        # We added several, but all on the same port
        elif all(param == added_params[0]
                 for param in added_params[1:]):
            return "Added DAT parameters to %s" % added_params[0]
        # We added several on different ports
        else:
            return "Added DAT parameters"
    # We only removed parameters
    elif removed_params and not added_params:
        # We removed one
        if len(removed_params) == 1:
            return "Removed DAT parameter from %s" % (
                removed_params[0])
        # We removed several, but all on the same port
        elif all(param == removed_params[0]
                 for param in removed_params[1:]):
            return "Removed DAT parameters from %s" % (
                removed_params[0])
        # We removed several from different ports
        else:
            return "Removed DAT parameters"
    # Both additions and deletions
    else:
        # Replaced a parameter
        if ((len(added_params), len(removed_params)) == (1, 1) and
                added_params[0] == removed_params[0]):
            return "Changed DAT parameter on %s" % added_params[0]
        # Did all kind of stuff
        else:
            if added_params:
                port = added_params[0]
            else:
                port = removed_params[0]
            # ... to a single port
            if all(param == port
                   for param in chain(added_params, removed_params)):
                return "Changed DAT parameters on %s" % port
            # ... to different ports
            else:
                return "Changed DAT parameters"


# We don't use vistrails.packages.spreadsheet.spreadsheet_execute:
# executePipelineWithProgress() because it doesn't update provenance
# We need to use the controller's execute_workflow_list() instead of calling
# the interpreter directly
def execute_pipeline(controller, pipeline,
                     reason, locator, version,
                     **kwargs):
    """Execute the pipeline while showing a progress dialog.
    """
    _ = translate('execute_pipeline')

    totalProgress = len(pipeline.modules)
    progress = QtGui.QProgressDialog(_("Executing..."),
                                     None,
                                     0, totalProgress)
    progress.setWindowTitle(_("Pipeline Execution"))
    progress.setWindowModality(QtCore.Qt.WindowModal)
    progress.show()

    def moduleExecuted(objId):
        progress.setValue(progress.value() + 1)
        QtCore.QCoreApplication.processEvents()

    if 'module_executed_hook' in kwargs:
        kwargs['module_executed_hook'].append(moduleExecuted)
    else:
        kwargs['module_executed_hook'] = [moduleExecuted]

    results, changed = controller.execute_workflow_list([(
        locator,        # locator
        version,        # version
        pipeline,       # pipeline
        DummyView(),    # view
        None,           # custom_aliases
        None,           # custom_params
        reason,         # reason
        None,           # sinks
        kwargs)])       # extra_info
    get_vistrails_application().send_notification('execution_updated')
    progress.setValue(totalProgress)
    progress.hide()
    progress.deleteLater()

    if not results[0].errors:
        return None
    else:
        module_id, error = next(results[0].errors.iteritems())
        return str(error)


MISSING_PARAMS = object()


def try_execute(controller, pipelineInfo):
    recipe = pipelineInfo.recipe

    if all(
            port.optional or port.name in recipe.parameters
            for port in recipe.plot.ports):
        # Get the pipeline
        controller.change_selected_version(pipelineInfo.version)
        pipeline = controller.current_pipeline

        # Execute the new pipeline
        error = execute_pipeline(
            controller,
            pipeline,
            reason="DAT recipe execution",
            locator=controller.locator,
            version=pipelineInfo.version)
        return error
    else:
        return MISSING_PARAMS
