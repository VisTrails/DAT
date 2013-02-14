"""Full tests creating pipeline from DAT.

"""


import unittest

from dat import DATRecipe
import dat.tests
from dat.tests import CallRecorder, FakeObj
from dat.vistrail_data import VistrailManager
from dat import vistrails_interface

from vistrails.core import get_vistrails_application
from vistrails.core.interpreter.default import get_default_interpreter
from vistrails.core.modules.sub_module import OutputPort
from vistrails.core.packagemanager import get_package_manager, PackageManager
from vistrails.core.utils import DummyView


class Test_generation(unittest.TestCase):
    _loaders = dict()

    @staticmethod
    def _new_loader(loader):
        Test_generation._loaders[loader.loader_tab_name] = loader()

    @classmethod
    def setUp(cls):
        cls._application = dat.tests.setup_application()
        if cls._application is None:
            cls.skipTest("No Application is available")

        if not Test_generation._loaders:
            cls._application.register_notification(
                    'dat_new_loader', cls._new_loader)

            pm = get_package_manager()

            pm.late_enable_package(
                'pkg_test_variables',
                {'pkg_test_variables': 'dat.tests.'})

            pm.late_enable_package(
                'pkg_test_plots',
                {'pkg_test_plots': 'dat.tests.'})

    def tearDown(self):
        pm = get_package_manager()
        def disable(codepath):
            try:
                pm.late_disable_package(codepath)
            except PackageManager.MissingPackage:
                pass
        disable('pkg_test_variables')
        disable('pkg_test_plots')

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

    def test_pipeline_creation(self):
        import dat.tests.pkg_test_plots.init as pkg_test_plots

        controller = self.vt_controller()
        vistraildata = VistrailManager(controller)
        loader = Test_generation._loaders.get('StrMaker')

        loader.v = 'Hello'
        vistraildata.new_variable('var1', loader.load())

        loader.v = 'world'
        vistraildata.new_variable('var2', loader.load())

        cellInfo = FakeObj(
                row=0,
                col=0,
                tab=FakeObj(
                        tabWidget=FakeObj(
                                tabText=lambda w: 'Sheet 1')))

        recipe = DATRecipe(
                pkg_test_plots.concat_plot,
                dict(
                        param1=vistraildata.get_variable('var1'),
                        param2=vistraildata.get_variable('var2')))

        pipelineInfo = vistrails_interface.create_pipeline(
                controller,
                recipe,
                cellInfo)

        controller.change_selected_version(pipelineInfo.version)

        result = CallRecorder()
        pkg_test_plots.Recorder.callback = result

        interpreter = get_default_interpreter()
        interpreter.execute(
                controller.current_pipeline,
                view=DummyView(),
                locator=controller.locator,
                current_version=pipelineInfo.version)

        call = (['Hello, world'], dict())
        self.assertEqual(result.calls, [call])
