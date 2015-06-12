from dat.packages import Variable, VariableOperation, OperationArgument
from dat.vistrails_interface.utils import resolve_descriptor

from vistrails.core.modules.basic_modules import Float, String


Float_desc = resolve_descriptor(Float)
String_desc = resolve_descriptor(String)


def float_op(op):
    def cb(op1, op2):
        new_var = Variable(type=Float_desc)
        calc = new_var.add_module(
            'org.vistrails.vistrails.pythoncalc:PythonCalc')
        calc.add_function('op', String_desc, op)
        op1.connect_to(calc, 'value1')
        op2.connect_to(calc, 'value2')
        new_var.select_output_port(calc, 'value')
        return new_var

    return VariableOperation(
        op,
        callback=cb,
        args=[
            OperationArgument('op1', Float_desc),
            OperationArgument('op2', Float_desc),
        ],
        return_type=Float_desc)


builtin_operations = {
    '+': [float_op('+')],
    '-': [float_op('-')],
    '*': [float_op('*')],
    '/': [float_op('/')],
}
