# Default variable name, if a variable loader can't provide a more specific one
DEFAULT_VARIABLE_NAME = "variable"

# MIME type of DAT variables
MIMETYPE_DAT_VARIABLE = 'X-Vistrails/DATVariable'

# MIME type of DAT plots
MIMETYPE_DAT_PLOT = 'X-Vistrails/DATPlot'


variable_format_1st_char = r'[A-Za-z_$@]'
variable_format_other_chars = r'[A-Za-z_$@0-9]'
variable_format = r'%s%s*' % (
        variable_format_1st_char,
        variable_format_other_chars)


class RecipeParameterValue(object):
    VARIABLE = 1
    CONSTANT = 2

    def __init__(self, variable=None, constant=None):
        if variable is not None and constant is None:
            self.type = self.VARIABLE
            self.variable = variable
        elif constant is not None and variable is None:
            self.type = self.CONSTANT
            self.constant = constant
        else:
            raise ValueError

    def __eq__(self, other):
        if not isinstance(other, RecipeParameterValue):
            return False
        if self.type != other.type:
            return False
        elif self.type == self.VARIABLE:
            return self.variable is other.variable
        else: # self.type == self.CONSTANT:
            return self.constant == other.constant

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        if self.type == self.VARIABLE:
            return hash((self.type, self.variable.name))
        else: # self.type == self.CONSTANT:
            return hash((self.type, self.constant))


class DATRecipe(object):
    """Just a simple class holding a Plot and its parameters.
    """
    def __init__(self, plot, parameters):
        self.plot = plot
        # str -> [RecipeParameterValue]
        self.parameters = {param: tuple(values)
                           for param, values in parameters.iteritems()
                           if values}
        self._hash = hash((
                self.plot,
                frozenset(self.parameters.iteritems())))

    def __eq__(self, other):
        if not isinstance(other, DATRecipe):
            return False
        return (self.plot, self.parameters) == (other.plot, other.parameters)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return self._hash


class PipelineInformation(object):
    """All the information DAT has on a plot.

    This is stored in VistrailsData. If an object doesn't exist for a version/
    cell, it is assumed not to be a DAT visualization.
    """
    def __init__(self, version, recipe, conn_map, port_map):
        self.version = version
        self.recipe = recipe
        # str -> [[conn_id]]
        self.conn_map = {param: tuple(tuple(conns) for conns in values)
                         for param, values in conn_map.iteritems()
                         if values}
        # str -> [(mod_id, port_name)]
        if port_map is None:
            self.port_map = None
        else:
            self.port_map = {param: tuple((mod_id, port_name)
                                          for mod_id, port_name in ports)
                             for param, ports in port_map.iteritems()}


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
