from dat.vistrail_data import VistrailManager

from dat.operations import InvalidExpression
from dat.operations.parsing import SYMBOL, NUMBER, OP, parse_expression
from dat.vistrails_interface import Variable, PipelineGenerator

from vistrails.core.modules.basic_modules import Float
from vistrails.core.modules.module_registry import get_module_registry


class ComputeVariable(object):
    def execute(self, controller):
        raise NotImplementedError


class GetExistingVariable(ComputeVariable):
    def __init__(self, vistraildata, varname):
        self._variable = vistraildata.get_variable(varname)
        if self._variable is None:
            raise InvalidExpression("Unknown variable %r" % varname)
        self.type = self._variable.type

    def execute(self, controller):
        return Variable.from_pipeline(controller, self._variable)


class BuildConstant(ComputeVariable):
    def __init__(self, value):
        self.value = value
        self.type = get_module_registry().get_descriptor_by_name(
                'edu.utah.sci.vistrails.basic',
                'Float')

    def execute(self, controller):
        generator = PipelineGenerator(controller)
        Float_desc = get_module_registry().get_descriptor(Float)
        module = generator.controller.create_module_from_descriptor(
                generator.controller.id_scope,
                Float_desc)
        generator.add_module(module)
        generator.update_function(module, 'value', [self.value])
        return Variable(
                type=Float_desc,
                controller=controller,
                generator=generator)


class ApplyOperation(ComputeVariable):
    def __init__(self, name, args):
        self._op = find_operation(name, [arg.type for arg in args])
        self.type = self._op.return_type
        self._args = args

    def execute(self, controller):
        """Recursively perform operations.
        """
        args = (arg.execute(controller) for arg in self._args)
        return apply_operation(self._op, args)


def resolve_symbols(vistraildata, expr):
    if expr[0] == SYMBOL:
        # Get an existing variable
        return GetExistingVariable(vistraildata, expr[1])
    elif expr[0] == NUMBER:
        # Build a constant module
        return BuildConstant(expr[1])
    elif expr[0] == OP:
        # Find the right operation, comparing argument number and types
        name = expr[1]
        args = [resolve_symbols(arg) for arg in expr[2:]]
        if all(isinstance(arg, BuildConstant) for arg in args):
            if name == '+':
                return BuildConstant(arg[0].value + arg[1].value)
            elif name == '-':
                return BuildConstant(arg[0].value - arg[1].value)
            elif name == '*':
                return BuildConstant(arg[0].value * arg[1].value)
            elif name == '/':
                return BuildConstant(arg[0].value / arg[1].value)
        return ApplyOperation(name, args)


def perform_operation(expression, controller=None):
    """Perform a variable operation from the given string.
    """
    # First, parse the expressions
    target, expr_tree = parse_expression(expression)

    # Find the actual operations & variables
    controller, root_version, output_module_id = (
            Variable._get_variables_root(controller))
    vistraildata = VistrailManager(controller)
    op_tree = resolve_symbols(vistraildata, expr_tree)

    # Build the new variable
    variable = op_tree.execute(controller)
    vistraildata.new_variable(target, variable)


def find_operation(name, args):
    """Choose the operation with the given name that accepts these arguments.
    """
    # TODO-dat : find_operation()


def apply_operation(op, args):
    """Apply an operation to build a new variable.

    Either load the subworkflow or wrap the parameter variables correctly and
    call the callback function.
    """
    # TODO-dat : apply_operation()
