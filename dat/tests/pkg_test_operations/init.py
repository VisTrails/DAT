from dat.packages import VariableOperation, OperationArgument

from vistrails.core.modules.basic_modules import Float, Integer, String
from vistrails.core.modules.vistrails_module import Module
from vistrails.packages.HTTP.init import HTTPFile


def nop(**kwargs):
    pass


overload_std_1 = VariableOperation(
    'overload_std',
    callback=nop,
    args=[
        OperationArgument('op1', Module),
        OperationArgument('op2', Module),
    ],
    return_type=Module)

overload_std_2 = VariableOperation(
    'overload_std',
    callback=nop,
    args=[
        OperationArgument('op1', HTTPFile),
        OperationArgument('op2', Integer),
    ],
    return_type=Module)

overload_std_3 = VariableOperation(
    'overload_std',
    callback=nop,
    args=[
        OperationArgument('op1', String),
        OperationArgument('op2', Integer),
    ],
    return_type=Module)

overload_std_4 = VariableOperation(
    'overload_std',
    callback=nop,
    args=[
        OperationArgument('op1', String),
        OperationArgument('op2', Float),
    ],
    return_type=Module)


class ModA(Module): pass

class ClassA(object): pass

class ClassB(object): pass

class ModB(ModA, ClassA): pass

class ModC(ModB, ClassB): pass

class ModD(ModA): pass

class ModE(Module): pass


overload_custom_1 = VariableOperation(
    'overload_custom',
    callback=nop,
    args=[
        OperationArgument('op1', ModA),
        OperationArgument('op2', ModD),
    ],
    return_type=Module)

overload_custom_2 = VariableOperation(
    'overload_custom',
    callback=nop,
    args=[
        OperationArgument('op1', ModB),
        OperationArgument('op2', ModD),
    ],
    return_type=Module)

overload_custom_3 = VariableOperation(
    'overload_custom',
    callback=nop,
    args=[
        OperationArgument('op1', ModE),
        OperationArgument('op2', ModD),
    ],
    return_type=Module)

overload_custom_4 = VariableOperation(
    'overload_custom',
    callback=nop,
    args=[
        OperationArgument('op1', ModB),
        OperationArgument('op2', ModE),
    ],
    return_type=Module)


_modules = [ModA, ModB, ModC, ModD, ModE]


_variable_operations = [
    overload_std_1,
    overload_std_2,
    overload_std_3,
    overload_std_4,

    overload_custom_1,
    overload_custom_2,
    overload_custom_3,
    overload_custom_4,
]
