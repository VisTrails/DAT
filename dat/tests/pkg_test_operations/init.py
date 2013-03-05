from dat.packages import VariableOperation

from vistrails.core.modules.basic_modules import Float, Integer
from vistrails.core.modules.vistrails_module import Module
from vistrails.packages.HTTP.init import HTTP, HTTPFile


def nop(**kwargs):
    pass


overload_std_1 = VariableOperation(
    'overload_std',
    callback=nop,
    args=[
        ('op1', Module),
        ('op2', Module),
    ],
    return_type=Module)

overload_std_2 = VariableOperation(
    'overload_std',
    callback=nop,
    args=[
        ('op1', Integer),
        ('op2', HTTPFile),
    ],
    return_type=Module)

overload_std_3 = VariableOperation(
    'overload_std',
    callback=nop,
    args=[
        ('op1', Float),
        ('op2', HTTPFile),
    ],
    return_type=Module)

overload_std_4 = VariableOperation(
    'overload_std',
    callback=nop,
    args=[
        ('op1', Float),
        ('op2', HTTP),
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
        ('op1', ModA),
        ('op2', ModD),
    ],
    return_type=Module)

overload_custom_2 = VariableOperation(
    'overload_custom',
    callback=nop,
    args=[
        ('op1', ModB),
        ('op2', ModD),
    ],
    return_type=Module)

overload_custom_3 = VariableOperation(
    'overload_custom',
    callback=nop,
    args=[
        ('op1', ModE),
        ('op2', ModD),
    ],
    return_type=Module)

overload_custom_4 = VariableOperation(
    'overload_custom',
    callback=nop,
    args=[
        ('op1', ModB),
        ('op2', ModE),
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
