"""Pipeline-generation code.
"""

from dat.vistrails_interface.utils import delete_linked

from vistrails.core.db.action import create_action
from vistrails.core.modules.module_registry import get_module_registry
from vistrails.core.vistrail.connection import Connection
from vistrails.core.vistrail.module import Module as PipelineModule


class PipelineGenerator(object):
    """A wrapper for simple operations that keeps a list of all modules.

    This wraps simple operations on the pipeline and keeps the list of
    VisTrails ops internally. It also keeps a list of all modules needed by
    VisTrails's layout function.
    """
    def __init__(self, controller):
        self.controller = controller
        self._version = controller.current_version
        self.operations = []
        self.all_modules = set(controller.current_pipeline.module_list)
        self.all_connections = set(controller.current_pipeline.connection_list)

    def _ensure_version(self):
        if self.controller.current_version != self._version:
            self.controller.change_selected_version(self._version)

    def append_operations(self, operations):
        for op in operations:
            if op[0] == 'add':
                if isinstance(op[1], PipelineModule):
                    self.all_modules.add(op[1])
                elif isinstance(op[1], Connection):
                    self.all_connections.add(op[1])
        self.operations.extend(operations)

    def copy_module(self, module):
        """Copy a VisTrails module to this controller.

        Returns the new module (that is not yet created in the vistrail!)
        """
        module = module.do_copy(True, self.controller.vistrail.idScope, {})
        self.operations.append(('add', module))
        self.all_modules.add(module)
        return module

    def add_module(self, module):
        self.operations.append(('add', module))
        self.all_modules.add(module)

    def connect_modules(self, src_mod, src_port, dest_mod, dest_port):
        self._ensure_version()
        new_conn = self.controller.create_connection(
            src_mod, src_port,
            dest_mod, dest_port)
        self.operations.append(('add', new_conn))
        self.all_connections.add(new_conn)
        return new_conn.id

    def connect_var(self, vt_var, dest_module, dest_portname):
        self._ensure_version()
        var_type_desc = get_module_registry().get_descriptor_by_name(
            vt_var.package, vt_var.module, vt_var.namespace)
        x = dest_module.location.x
        y = dest_module.location.y

        # Adapted from VistrailController#connect_vistrail_var()
        var_module = self.controller.find_vistrail_var_module(vt_var.uuid)
        if var_module is None:
            var_module = self.controller.create_vistrail_var_module(
                var_type_desc,
                x, y,
                vt_var.uuid)
            self.operations.append(('add', var_module))
        elif self.controller.check_vistrail_var_connected(var_module,
                                                          dest_module,
                                                          dest_portname):
            return
        connection = self.controller.create_connection(
            var_module, 'value', dest_module, dest_portname)
        self.operations.append(('add', connection))

    def update_function(self, module, portname, values):
        self._ensure_version()
        self.operations.extend(self.controller.update_function_ops(
            module, portname, values))

    def delete_linked(self, modules, **kwargs):
        """Wrapper for delete_linked().

        This calls delete_linked with the controller and list of operations,
        and updates the internal list of all modules to be layout.
        """
        self._ensure_version()
        deleted_ids = delete_linked(
            self.controller, modules, self.operations, **kwargs)
        self.all_modules = set(
            m
            for m in self.all_modules
            if m.id not in deleted_ids)
        self.all_connections = set(
            c
            for c in self.all_connections
            if (c.source.moduleId not in deleted_ids and
                c.destination.moduleId not in deleted_ids))

    def delete_modules(self, modules):
        self.delete_linked(modules, depth=0)

    def perform_action(self):
        """Layout all the modules and create the action.
        """
        self._ensure_version()

        pipeline = self.controller.current_pipeline

        self.operations.extend(self.controller.layout_modules_ops(
            old_modules=[m
                         for m in self.all_modules
                         if m.id in pipeline.modules],
            new_modules=[m
                         for m in self.all_modules
                         if m.id not in pipeline.modules],
            new_connections=[c
                             for c in self.all_connections
                             if c.id not in pipeline.connections],
            preserve_order=True))

        action = create_action(self.operations)
        self.controller.add_new_action(action)
        return self.controller.perform_action(action)


def add_constant_module(generator, descriptor, constant, plot_ports):
    module = generator.controller.create_module_from_descriptor(descriptor)
    generator.add_module(module)
    generator.update_function(module, 'value', [constant])

    connection_ids = []
    for output_mod, output_port in plot_ports:
        connection_ids.append(generator.connect_modules(
            module,
            'value',
            output_mod,
            output_port))

    return connection_ids
