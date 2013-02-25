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

from dat.gui import translate

from dat.vistrails_interface import Plot, DataPort, ConstantPort, Variable, \
    CustomVariableLoader, FileVariableLoader


__all__ = ['Plot', 'DataPort', 'ConstantPort', 'Variable',
           'CustomVariableLoader', 'FileVariableLoader',
           'translate']
