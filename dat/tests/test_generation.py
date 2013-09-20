"""Full tests creating pipeline from DAT.

"""


import os
import unittest

from dat import DATRecipe, RecipeParameterValue
import dat.tests
from dat.tests import CallRecorder, FakeObj
from dat.vistrail_data import VistrailManager
from dat import vistrails_interface
from dat.vistrails_interface import get_upgraded_pipeline, Variable

from vistrails.core import get_vistrails_application
from vistrails.core.db.locator import XMLFileLocator
from vistrails.core.interpreter.default import get_default_interpreter
import vistrails.core.modules.basic_modules as basic
from vistrails.core.modules.sub_module import OutputPort
from vistrails.core.packagemanager import get_package_manager, PackageManager
from vistrails.core.utils import DummyView


class Test_generation(unittest.TestCase):
    _loaders = dict()

    @staticmethod
    def _new_loader(loader):
        Test_generation._loaders[loader.name] = loader()

    @classmethod
    def setUpClass(cls):
        cls._application = dat.tests.setup_application()
        if cls._application is None:
            raise unittest.SkipTest("No Application is available")

        cls._application.register_notification(
                'dat_new_loader', cls._new_loader)

        pm = get_package_manager()

        pm.late_enable_package(
            'pkg_test_variables',
            {'pkg_test_variables': 'dat.tests.'})

        pm.late_enable_package(
            'pkg_test_plots',
            {'pkg_test_plots': 'dat.tests.'})

    @classmethod
    def tearDownClass(cls):
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
        view = app.builderWindow.new_vistrail()
        controller = view.get_controller()
        VistrailManager.set_controller(controller, register=True)
        return controller

    def test_variable(self):
        controller = self.vt_controller()
        loader = Test_generation._loaders.get('MyVariableLoader')
        self.assertIsNotNone(loader)

        varname = 'mytest'
        variable = loader.load()
        self.assertIsNotNone(variable)
        VistrailManager(controller).new_variable(varname, variable)

        tag = controller.vistrail.get_tag_str('dat-var-%s' % varname)
        controller.change_selected_version( tag.action_id)

        pipeline = controller.current_pipeline
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
                'org.vistrails.vistrails.basic:Float')

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
                column=0,
                tab=FakeObj(
                        tabWidget=FakeObj(
                                tabText=lambda w: 'Sheet 1')))

        recipe = DATRecipe(
                pkg_test_plots.concat_plot,
                {
                    'param1': (
                        RecipeParameterValue(
                                variable=vistraildata.get_variable('var1')),
                    ),
                    'param2': (
                        RecipeParameterValue(
                                variable=vistraildata.get_variable('var2')),
                    ),
                    'param3': (
                        RecipeParameterValue(
                                constant="!"),
                    ),
                })

        pipelineInfo = vistrails_interface.create_pipeline(
                controller,
                recipe,
                cellInfo.row,
                cellInfo.column,
                None) # This plot has no cell module so this is fine

        controller.change_selected_version(pipelineInfo.version)

        result = CallRecorder()
        pkg_test_plots.Recorder.callback = result

        interpreter = get_default_interpreter()
        interpreter.execute(
                controller.current_pipeline,
                view=DummyView(),
                locator=controller.locator,
                current_version=pipelineInfo.version)

        call = (['Hello, world!'], dict())
        self.assertEqual(result.calls, [call])


class Test_variable_creation(unittest.TestCase):
    def test_var_type(self):
        a_var = Variable(type=basic.Float)
        a_mod = a_var.add_module('org.vistrails.vistrails.basic:String')
        with self.assertRaises(ValueError):
            a_var.select_output_port(a_mod, 'value')

        b_var = Variable(type=basic.String)
        b_mod = b_var.add_module('org.vistrails.vistrails.basic:String')
        with self.assertRaises(ValueError):
            b_var.select_output_port(b_mod, 'nonexistent')
        b_mod2 = b_var.add_module('org.vistrails.vistrails.basic:Integer')
        with self.assertRaises(ValueError):
            b_var.select_output_port(a_mod, 'value_as_string')
        b_var.select_output_port(b_mod, 'value')
        with self.assertRaises(ValueError):
            b_var.select_output_port(b_mod2, 'value_as_string')

    def test_mod_addfunction(self):
        var = Variable(type=basic.Integer)
        mod = var.add_module('org.vistrails.vistrails.basic:Integer')
        mod.add_function('value', basic.Integer, 42)
        mod.add_function('value', [basic.Integer], [16])
        with self.assertRaises(ValueError) as cm:
            mod.add_function('value', [basic.Float], [17.6])
        self.assertTrue("incompatible types" in cm.exception.args[0])
        with self.assertRaises(ValueError) as cm:
            mod.add_function('value', [basic.Integer], [])
        self.assertTrue("different number" in cm.exception.args[0])
        with self.assertRaises(ValueError) as cm:
            mod.add_function('value', [basic.Integer, basic.Integer], [13, 28])
        self.assertTrue("different number" in cm.exception.args[0])
        with self.assertRaises(ValueError) as cm:
            mod.add_function('nonexistent', [basic.Integer], [18])
        self.assertTrue("non-existent input port" in cm.exception.args[0])

    def test_connect_outputport(self):
        from vistrails.core.modules.module_registry import PortsIncompatible
        var = Variable(type=basic.String)
        mod1 = var.add_module('org.vistrails.vistrails.basic:Float')
        mod2 = var.add_module('org.vistrails.vistrails.basic:String')
        with self.assertRaises(PortsIncompatible):
            mod1.connect_outputport_to('value', mod2, 'value')
        var2 = Variable(type=basic.String)
        mod3 = var2.add_module('org.vistrails.vistrails.basic:Float')
        with self.assertRaises(ValueError) as cm:
            mod1.connect_outputport_to('value', mod3, 'value')
        self.assertTrue("same Variable" in cm.exception.args[0])

    def test_get_var_type(self):
        locator = XMLFileLocator(os.path.join(
                os.path.dirname(__file__),
                'variables.xml'))
        vistrail = locator.load()

        desc_var1 = Variable.read_type(get_upgraded_pipeline(
                vistrail,
                'dat-var-var1'))
        self.assertEqual(
                desc_var1.module,
                basic.Float)
        desc_var2 = Variable.read_type(get_upgraded_pipeline(
                vistrail,
                'dat-var-var2'))
        self.assertEqual(
                desc_var2.module,
                basic.String)
