"""Tests for function manipulating pipelines or vistrail files.

"""


import unittest

import dat.tests

from vistrails.core.modules.module_registry import get_module_registry
from vistrails.core.vistrail.controller import VistrailController
from vistrails.core.vistrail.vistrail import Vistrail


class Test_vistrails_interface(unittest.TestCase):
    def setUp(self):
        if dat.tests.setup_application() is None:
            self.skipTest("No Application is available")

    def test_resolve_descriptor(self):
        """Tests the resolve_descriptor() function.
        """
        from dat.vistrails_interface import resolve_descriptor
        from vistrails.core.modules.basic_modules import String
        from vistrails.packages.HTTP.init import HTTPFile

        reg = get_module_registry()
        desc_String = reg.get_descriptor(String)
        desc_HTTPFile = reg.get_descriptor(HTTPFile)

        self.assertRaises(
                TypeError,
                lambda: resolve_descriptor(42))
        self.assertEqual(
                resolve_descriptor(desc_HTTPFile),
                desc_HTTPFile)
        self.assertEqual(
                resolve_descriptor('org.vistrails.vistrails.http:HTTPFile'),
                desc_HTTPFile)
        self.assertEqual(
                resolve_descriptor('org.vistrails.vistrails.http:HTTPFile',
                                   'org.vistrails.vistrails.basic'),
                desc_HTTPFile)
        self.assertEqual(
                resolve_descriptor('org.vistrails.vistrails.http:HTTPFile',
                                   'org.vistrails.vistrails.http'),
                desc_HTTPFile)
        self.assertEqual(
                resolve_descriptor('HTTPFile',
                                   'org.vistrails.vistrails.http'),
                desc_HTTPFile)
        self.assertEqual(
                resolve_descriptor(HTTPFile),
                desc_HTTPFile)
        self.assertEqual(
                resolve_descriptor(String),
                desc_String)
        self.assertEqual(
                resolve_descriptor('String', 'org.vistrails.vistrails.basic'),
                desc_String)
        self.assertEqual(
                resolve_descriptor('String'),
                desc_String)

    def make_pipeline(self):
        """Creates an example pipeline that is used to conduct tests.
        """
        vistrail = Vistrail()
        controller = VistrailController(vistrail)
        controller.change_selected_version(0)

        # 0     1    2   7   8
        # |    / \        \ /
        # 3   4   5        9
        #         |       / \
        #         6     10   11
        modules = [controller.add_module('org.vistrails.vistrails.basic',
                                         'String')
                   for i in xrange(12)]
        def connect(outmod, inmod):
            controller.add_connection(
                    modules[outmod].id,
                    'value',
                    modules[inmod].id,
                    'value')
        for (outmod, inmod) in [(0, 3),
                                (1, 4), (1, 5), (5, 6),
                                (7, 9), (8, 9), (9, 10), (9, 11)]:
            connect(outmod, inmod)

        return controller, modules

    def test_delete_linked(self):
        """Tests the delete_linked() function.
        """
        from dat.vistrails_interface import delete_linked
        from vistrails.core.db.action import create_action

        def test_delete(to_delete, expected_survivors,
                        controller=None, modules=None,
                        **kwargs):
            if controller is None:
                controller, modules = self.make_pipeline()
            rmodules = {m.id: i for i, m in enumerate(modules)}
            to_delete = [modules[i] for i in to_delete]

            operations = []
            delete_linked(controller, to_delete, operations, **kwargs)
            action = create_action(operations)
            controller.add_new_action(action)
            controller.change_selected_version(
                    controller.perform_action(action))

            survivors = [rmodules[m.id]
                         for m in controller.current_pipeline.module_list]
            survivors.sort()
            self.assertEqual(survivors, expected_survivors)

        test_delete([5], [0, 2, 3, 7, 8, 9, 10, 11])
        test_delete([8], [0, 1, 2, 3, 4, 5, 6])
        test_delete([3, 2, 11], [1, 4, 5, 6])
        controller, modules = self.make_pipeline()
        test_delete([6, 7], [0, 1, 2, 3, 4, 5, 11], controller, modules,
                    module_filter=lambda m: m.id not in (modules[5].id,
                                                         modules[11].id))
        controller, modules = self.make_pipeline()
        test_delete([1, 7], [0, 2, 3, 6, 10, 11], controller, modules,
                    connection_filter=lambda c: c.source.moduleId not in (
                            modules[5].id, modules[9].id))
        test_delete([3, 6, 7], [2, 4],
                    depth=2)

    def test_find_modules_by_type(self):
        """Tests the find_modules_by_type() function.
        """
        vistrail = Vistrail()
        controller = VistrailController(vistrail)
        controller.change_selected_version(0)

        mod1 = controller.add_module('org.vistrails.vistrails.basic',
                                     'String')
        mod2 = controller.add_module('org.vistrails.vistrails.basic',
                                     'Float')
        mod3 = controller.add_module('org.vistrails.vistrails.basic',
                                     'String')
        mod4 = controller.add_module('org.vistrails.vistrails.basic',
                                     'Integer')

        from dat.vistrails_interface import find_modules_by_type
        from vistrails.core.modules.basic_modules import Boolean, Float, String

        self.assertEqual(
                set(m.id for m in find_modules_by_type(
                         controller.current_pipeline,
                         [String])),
                set([mod1.id, mod3.id]))

        self.assertEqual(
                [m.id for m in find_modules_by_type(
                         controller.current_pipeline,
                         [Float])],
                [mod2.id, mod4.id])

        self.assertEqual(
                find_modules_by_type(
                        controller.current_pipeline,
                        [Boolean]),
                [])

    def test_describe_update(self):
        """Tests the describe_dat_update() function.
        """
        from dat.vistrails_interface import describe_dat_update

        self.assertEqual(
                describe_dat_update(
                        ['port'],
                        []),
                "Added DAT parameter to port")
        self.assertEqual(
                describe_dat_update(
                        ['port', 'port'],
                        []),
                "Added DAT parameters to port")
        self.assertEqual(
                describe_dat_update(
                        ['port', 'port'],
                        ['port']),
                "Changed DAT parameters on port")
        self.assertEqual(
                describe_dat_update(
                        ['port'],
                        ['port']),
                "Changed DAT parameter on port")
        self.assertEqual(
                describe_dat_update(
                        [],
                        ['port']),
                "Removed DAT parameter from port")
        self.assertEqual(
                describe_dat_update(
                        [],
                        ['port', 'port']),
                "Removed DAT parameters from port")
        self.assertEqual(
                describe_dat_update(
                        ['a', 'b'],
                        []),
                "Added DAT parameters")
        self.assertEqual(
                describe_dat_update(
                        [],
                        ['a', 'b']),
                "Removed DAT parameters")
        self.assertEqual(
                describe_dat_update(
                        ['port', 'port'],
                        ['port']),
                "Changed DAT parameters on port")
        self.assertEqual(
                describe_dat_update(
                        ['a', 'b'],
                        ['a']),
                "Changed DAT parameters")
        self.assertEqual(
                describe_dat_update(
                        ['a'],
                        ['b']),
                "Changed DAT parameters")
