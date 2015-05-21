"""Interface with VisTrails packages.

This is the only module that VisTrails packages need to import. It provides
the classes and methods necessary to define plot types and variable loaders.

You might want to maintain compatibility with VisTrails, like so:
try:
    import dat.packages
except ImportError:
    pass # This happens if the package was imported from VisTrails, not from
         # DAT
         # In that case, don't define plots or variable loaders.
else:
    # Create a translator (optional)
    _ = dat.packages.translate('packages.MyPackage')

    _plots = [
        Plot(name="...",
             subworkflow="{package_dir}/....xml",
             description=_("..."),
             ports=[        # You don't have to list the ports, they can be
                 Port(...), # discovered from the subworkflow. If you do,
                 ...]),     # warnings will be issued for missing/wrong ports.
    ]

    class MyLoader(dat.packages.CustomVariableLoader):
        ...

    _variable_loaders = [
        MyLoader: _("My new loader"),
    ]
"""

import os
import re

import dat
from dat.gui import translate
from dat.gui.operation_wizard import OperationWizard
from dat.vistrails_interface import Plot, DataPort, ConstantPort, Variable, \
    CustomVariableLoader, FileVariableLoader, \
    VariableOperation, OperationArgument, \
    get_variable_value


_re_1st = re.compile(dat.variable_format_1st_char)
_re_other = re.compile(dat.variable_format_other_chars)


def derive_varname(param, remove_ext=False, remove_path=False, default=None,
                   prefix='', suffix=''):
    """Derives a proper variable name from something else, like a file name.
    """
    if remove_path:
        param = os.path.basename(param)
    if remove_ext:
        dot = param.rfind('.')
        if dot != -1:
            param = param[:dot]
    if not param:
        return default
    varname = str(prefix)
    if not prefix:
        if _re_1st.match(param[0]) is not None:
            varname += param[0]
        elif _re_other.match(param[0]) is not None:
            varname += '_' + param[0]
        pos = 1
    else:
        pos = 0
    while pos < len(param):
        if _re_other.match(param[pos]) is not None:
            varname += param[pos]
        else:
            varname += '_'
        pos += 1
    return varname + suffix


__all__ = ['Plot', 'DataPort', 'ConstantPort', 'Variable',
           'CustomVariableLoader', 'FileVariableLoader',
           'VariableOperation', 'OperationArgument', 'OperationWizard',
           'translate', 'derive_varname', 'get_variable_value']
