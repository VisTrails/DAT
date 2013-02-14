from dat.vistrails_interface import Variable, CustomVariableLoader, Plot, Port

import vistrails.core.modules.basic_modules as basic
from vistrails.core.modules.vistrails_module import Module, NotCacheable


class Recorder(NotCacheable, Module):
    _input_ports = [('value', '(edu.utah.sci.vistrails.basic:Module)')]

    def compute(self):
        v = self.getInputFromPort('value')
        Recorder.callback(v)


_modules = [Recorder]


class StrMaker(CustomVariableLoader):
    def load(self):
        var = Variable(type=basic.String)
        mod = var.add_module(basic.String)
        mod.add_function('value', basic.String, self.v)
        var.select_output_port(mod, 'value')
        return var


_variable_loaders = {
        StrMaker: "StrMaker"}


concat_plot = Plot(
        name="Concatenator",
        subworkflow='{package_dir}/concat.xml',
        description="Plot used internally to perform tests",
        ports=[
                Port(name='param1', type=basic.String, optional=False),
                Port(name='param2', type=basic.String, optional=True)])

_plots = [concat_plot]
