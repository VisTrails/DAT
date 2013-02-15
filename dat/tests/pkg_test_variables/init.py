from dat.vistrails_interface import Variable, CustomVariableLoader

import vistrails.core.modules.basic_modules as basic
from vistrails.core.modules.module_registry import get_module_registry
import vistrails.packages.pythonCalc.init as pythoncalc


class MyVariableLoader(CustomVariableLoader):
    def load(self):
        var = Variable(type=basic.Float)
        reg = get_module_registry()
        calc = var.add_module(pythoncalc.PythonCalc)
        op1 = var.add_module('edu.utah.sci.vistrails.basic:Float')
        op2 = var.add_module(basic.Float)
        op1.add_function('value', [basic.Float], ['17.63'])
        op1.add_function('value', basic.Float, '24.37')
        op1.connect_outputport_to('value', calc, 'value1')
        op2.connect_outputport_to('value', calc, 'value2')
        calc.add_function('op', basic.String, '+')
        var.select_output_port(calc, 'value')
        return var


_variable_loaders = {
        MyVariableLoader: "MyVariableLoader"}
