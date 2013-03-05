import inspect
import os, os.path


# Default variable name, if a variable loader can't provide a more specific one
DEFAULT_VARIABLE_NAME = "variable"

# MIME type of DAT variables
MIMETYPE_DAT_VARIABLE = 'X-Vistrails/DATVariable'

# MIME type of DAT plots
MIMETYPE_DAT_PLOT = 'X-Vistrails/DATPlot'


variable_format = r'[A-Za-z_$@][A-Za-z_$@0-9]*'


class DATRecipe(object):
    """Just a simple class holding a Plot and its parameters.
    """
    def __init__(self, plot, variables, constants):
        self.plot = plot
        self.variables = dict(variables)
        self.constants = dict(constants)
        self._hash = hash((
                self.plot,
                frozenset(self.variables.iteritems()),
                frozenset(self.constants.iteritems())))

    def __eq__(self, other):
        if not isinstance(other, DATRecipe):
            raise TypeError
        return (self.plot, self.variables, self.constants) == (
                other.plot, other.variables, other.constants)
    
    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return self._hash
    
    def get_plot_modules(self, plot, pipeline):
        #TODO: implement
        return pipeline.module_list

class PipelineInformation(object):
    """All the information DAT has on a plot.

    This is stored in VistrailsData. If an object doesn't exist for a version/
    cell, it is assumed not to be a DAT visualization.
    """
    def __init__(self, version, recipe, port_map=None, var_map=None):
        self.version = version
        self.recipe = recipe
        # {param: [(mod_id, port_name)]}
        self.port_map = dict(port_map) if port_map is not None else None
        # {param: [conn_id: int]}
        self.var_map = dict(var_map) if var_map is not None else None


class BaseVariableLoader(object):
    def __init__(self):
        self.default_variable_name_observer = None

    def reset(self):
        """Resets the widget so it can be used again.

        Implement this in subclasses to reset the widget.
        """
        pass

    def get_default_variable_name(self):
        """Default name for the variable that will be loaded.

        You should re-implement this to return a sensible default name for the
        variable that will be loaded. The user can edit it if need be.
        You don't need to worry about already taken names, this default will be
        made unique if need be.
        """
        return DEFAULT_VARIABLE_NAME

    def default_variable_name_changed(self, new_default_name):
        """Call this function to signal that the default variable name changed.

        This can happen if the user selected a different file, ...
        """
        if self.default_variable_name_observer is not None:
            self.default_variable_name_observer(self, new_default_name)


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
    def __init__(self, name, args, return_type,
             callback=None, subworkflow=None, symmetric=False):
        self.name = name
        self.parameters = args
        self.return_type = return_type
        if callback is not None and subworkflow is not None:
            raise ValueError("VariableOperation() got both callback and "
                             "subworkflow parameters")
        if callback is None and subworkflow is None:
            raise ValueError("VariableOperation() got neither callback nor "
                             "subworkflow parameters")
        self.callback = callback
        self.subworkflow = subworkflow
        self.symmetric = symmetric


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
