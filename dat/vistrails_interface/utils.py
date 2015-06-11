"""General low-level utilities for VisTrails interaction.
"""

import sys

from vistrails.core.modules.basic_modules import Constant
from vistrails.core.modules.module_descriptor import ModuleDescriptor
from vistrails.core.modules.module_registry import get_module_registry
from vistrails.core.modules.utils import parse_descriptor_string
from vistrails.core.modules.vistrails_module import Module
from vistrails.core.vistrail.controller import VistrailController


def resolve_descriptor(param, package_identifier=None):
    """Resolve a type specifier to a ModuleDescriptor.

    This accepts different arguments and turns it into a ModuleDescriptor:
      * a ModuleDescriptor
      * a Module object
      * a descriptor string

    It should be used when accepting type specifiers from third-party code.

    The optional 'package_identifier' parameter gives the context in which to
    resolve module names; it is passed to parse_descriptor_string().
    """
    reg = get_module_registry()

    if isinstance(param, str):
        d_tuple = parse_descriptor_string(param, package_identifier)
        return reg.get_descriptor_by_name(*d_tuple)
    elif isinstance(param, type) and issubclass(param, Module):
        return reg.get_descriptor(param)
    elif isinstance(param, ModuleDescriptor):
        return param
    else:
        raise TypeError("resolve_descriptor() argument must be a Module "
                        "subclass or str object, not '%s'" % type(param))


def get_upgraded_pipeline(vistrail, version=None):
    """This is similar to Vistrail#getPipeline() but performs upgrades.

    getPipeline() can fail if the original pipeline has a different version.
    In contrast, this function will update the pipeline first using a
    controller.
    """
    if version is None:
        version = vistrail.get_latest_version()
    elif isinstance(version, (int, long)):
        pass
    elif isinstance(version, basestring):
        version = vistrail.get_tag_str(version).action_id
    else:
        raise TypeError

    controller = VistrailController(vistrail)
    controller.recompute_terse_graph()  # FIXME : this shouldn't be needed...
    controller.do_version_switch(version)
    return controller.current_pipeline


def get_function(module, function_name):
    """Get the value of a function of a pipeline module.
    """
    for function in module.functions:
        if function.name == function_name:
            if len(function.params) > 0:
                return function.params[0].strValue
    return None


def read_port_specs(pipeline, port):
    default_type = None
    default_value = None

    # First: try from the InputPort's 'Default' port
    # Connections to the 'Default' port
    connections = [c
                   for c in pipeline.connection_list
                   if (c.destination.moduleId == port.id and
                       c.destination.name == 'Default')]
    if len(connections) > 1:
        raise ValueError("multiple default values set")
    elif len(connections) == 1:
        module = pipeline.modules[connections[0].source.moduleId]
        module_type = module.module_descriptor.module
        if not issubclass(module_type, Constant):
            raise ValueError("not a Constant")
        default_type, default_value = (
            module_type, get_function(module, 'value'))

    # Connections from the 'InternalPipe' port
    connections = [c
                   for c in pipeline.connection_list
                   if (c.source.moduleId == port.id and
                       c.source.name == 'InternalPipe')]
    if len(connections) != 1:
        # Can't guess anything here
        return default_type, default_value, None, None
    module = pipeline.modules[connections[0].destination.moduleId]
    d_port_name = connections[0].destination.name
    for d_port in module.destinationPorts():
        if d_port.name != d_port_name:
            continue
        descriptors = d_port.descriptors()
        if len(descriptors) != 1:
            break
        if ((default_type, default_value is None, None) and
                d_port.defaults and d_port.defaults[0]):
            default_type = descriptors[0].module
            default_value = d_port.defaults[0]
        psi = d_port.port_spec_items[0]
        if psi.entry_type is not None and psi.entry_type.startswith('enum'):
            entry_type, enum_values = psi.entry_type, psi.values
        else:
            entry_type, enum_values = None, None
        return default_type, default_value, entry_type, enum_values

    return default_type, default_type, None, None


def walk_modules(pipeline, modules,
                 module_filter=None,
                 connection_filter=None,
                 depth=sys.maxint):
    if module_filter is None:
        module_filter = lambda m: True
    if connection_filter is None:
        connection_filter = lambda m: True

    # Build a map of the connections in which each module takes part
    module_connections = dict()
    for connection in pipeline.connection_list:
        for mod in (connection.source.moduleId,
                    connection.destination.moduleId):
            conns = module_connections.setdefault(mod, set())
            conns.add(connection)

    visited_connections = set()

    if isinstance(modules, (list, tuple, set)):
        open_list = modules
    else:
        open_list = [modules]

    selected = set(iter(open_list))

    # At each step
    while depth > 0 and open_list:
        new_open_list = []
        # For each module considered
        for module in open_list:
            # For each connection it takes part in
            for connection in module_connections.get(module.id, []):
                # If that connection passes the filter
                if (connection not in visited_connections and
                        connection_filter(connection)):
                    # Get the other module
                    if connection.source.moduleId == module.id:
                        other_mod = connection.destination.moduleId
                    else:
                        other_mod = connection.source.moduleId
                    other_mod = pipeline.modules[other_mod]
                    if other_mod in selected:
                        continue
                    # And if it passes the filter
                    if module_filter(other_mod):
                        # Select it
                        selected.add(other_mod)
                        # And add it to the list
                        new_open_list.append(other_mod)
                visited_connections.add(connection)

        open_list = new_open_list
        depth -= 1

    conn_selected = set()
    for module in selected:
        conn_selected.update(module_connections.get(module.id, []))

    return selected, conn_selected


def delete_linked(controller, modules, operations,
                  module_filter=None,
                  connection_filter=None,
                  depth=sys.maxint):
    """Delete all modules and connections linked to the specified modules.

    module_filter is an optional function called during propagation to modules.

    connection_filter is an optional function called during propagation to
    connections.

    depth_limit is an optional integer limiting the depth of the operation.
    """
    to_delete, conn_to_delete = walk_modules(
        controller.current_pipeline,
        modules,
        module_filter,
        connection_filter,
        depth)
    operations.extend(('delete', conn) for conn in conn_to_delete)
    operations.extend(('delete', module) for module in to_delete)

    return set(mod.id for mod in to_delete)


def find_modules_by_type(pipeline, moduletypes):
    """Finds all modules that subclass one of the given types in the pipeline.
    """
    moduletypes = tuple(moduletypes)
    result = []
    for module in pipeline.module_list:
        desc = module.module_descriptor
        if issubclass(desc.module, moduletypes):
            result.append(module)
    return result
