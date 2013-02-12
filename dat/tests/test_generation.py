"""Full tests creating pipeline from DAT.

"""


import unittest

import dat.tests

from dat.vistrail_data import VistrailManager
from dat import vistrails_interface

from vistrails.core import get_vistrails_application
from vistrails.core.modules.sub_module import OutputPort
from vistrails.core.packagemanager import get_package_manager


class Test_generation(unittest.TestCase):
    _loaders = dict()

    @staticmethod
    def _new_loader(loader):
        Test_generation._loaders[loader.loader_tab_name] = loader()

    def setUp(self):
        self._application = dat.tests.setup_application()
        if self._application is None:
            self.skipTest("No Application is available")

        if not Test_generation._loaders:
            self._application.register_notification(
                    'dat_new_loader', self._new_loader)

            pm = get_package_manager()

            pm.late_enable_package(
                'pkg_test_variables',
                {'pkg_test_variables': 'dat.tests.'})

    def tearDown(self):
        pm = get_package_manager()
        pm.late_disable_package('pkg_test_variables')

    @staticmethod
    def vt_controller():
        app = get_vistrails_application()
        app.builderWindow.new_vistrail()
        return app.get_controller()

    def test_variable(self):
        controller = self.vt_controller()
        loader = Test_generation._loaders.get('MyVariableLoader')
        self.assertIsNotNone(loader)

        varname = 'mytest'
        variable = loader.load()
        self.assertIsNotNone(variable)
        VistrailManager(controller).new_variable(varname, variable)

        controller.change_selected_version(
                controller.vistrail.get_tag_str('dat-var-%s' % varname),
                from_root=True)

        pipeline = controller.vistrail.getPipeline('dat-var-%s' % varname)
        self.assertEqual(len(pipeline.module_list), 4)
        # Float(17.63), Float(24.37), PythonCalc('+'), OutputPort

        output_port = vistrails_interface.find_modules_by_type(
                pipeline,
                [OutputPort])
        self.assertEqual(len(output_port), 1)
        output_port, = output_port
        self.assertEqual(
                vistrails_interface.get_function(output_port, 'name'),
                'value')
        self.assertEqual(
                vistrails_interface.get_function(output_port, 'spec'),
                'edu.utah.sci.vistrails.basic:Float')
