from dat.vistrail_data import VistrailManager

from dat.operations.parsing import SYMBOL, NUMBER, OP, parse_expression


def resolve_symbols(vistraildata, expr):
    if expr[0] == SYMBOL:
        # TODO-dat : find the variable
        pass
    elif expr[0] == NUMBER:
        # TODO-dat : other constants (strings?)
        # What format do we want to use here, to pass stuff to operations?
        pass
    elif expr[0] == OP:
        # TODO-dat : find the right operation, comparing argument number and
        # types
        pass


def perform_operation(controller, expression):
    """Perform a variable operation from the given string.
    """
    # First, parse the expressions
    target, expr_tree = parse_expression(expression)

    # Find the actual operations & variables
    op_tree = resolve_symbols(VistrailManager(controller), expr_tree)
