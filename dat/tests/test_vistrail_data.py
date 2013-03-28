"""Tests for dat.vistrail_data.

"""


import unittest

from dat import RecipeParameterValue, DATRecipe
from dat.global_data import GlobalManager
from dat.tests import FakeObj
from dat.vistrail_data import VistrailData


class Test_annotations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        class FakeVariable(object):
            def __init__(self, name):
                self.name = name
            def __eq__(self, other):
                return self.name == other.name

        cls.plot = FakeObj(name='My Plot',
                           package_identifier='tests.dat.vistrail_data')
        cls.var1 = FakeVariable('var1')
        cls.var2 = FakeVariable('var2')
        cls.var3 = FakeVariable('var3')
        all_vars = dict(var1=cls.var1, var2=cls.var2, var3=cls.var3)
        def get_variable(name):
            return all_vars.get(name)
        cls.vistraildata = FakeObj(get_variable=get_variable)

        cls.recipe = DATRecipe(
                cls.plot,
                {
                    'param1': (
                        RecipeParameterValue(
                            variable=cls.var1),
                        RecipeParameterValue(
                            variable=cls.var2),
                    ),
                    'param2': (
                        RecipeParameterValue(
                            constant='test\'";b=c,r\xC3\xA9mi'),
                    ),
                    'param3': (
                        RecipeParameterValue(
                            variable=cls.var3),
                    ),
                })
        cls.conn_map = {
                'param1': (
                    (1, 2),
                    (5,),
                ),
                'param2': (
                    (4,),
                ),
                'param3': (
                    (3,),
                ),
            }
        cls.port_map = {
                'param1': (
                    (1, 'port1'), (2, 'port2'),
                ),
                'param2': (
                ),
                'param3': (
                    (3, 'port3'),
                ),
            }

    def test_build_recipe(self):
        """Tests the _build_annotation() method.
        """
        self.assertEqual(
                VistrailData._build_recipe_annotation(
                        self.recipe,
                        self.conn_map),
                'tests.dat.vistrail_data,My Plot'
                ';param1=v='
                    'var1:1,2|'
                    'var2:5'
                ';param2=c='
                    'test%27%22%3Bb%3Dc%2Cr%C3%A9mi:4'
                ';param3=v='
                    'var3:3')

    def test_read_recipe(self):
        """Tests the _read_annotation() method.
        """
        # Patch GlobalManager
        old_get_plot = GlobalManager.get_plot
        def get_plot(pkg_id, name):
            if name != 'My Plot' or pkg_id != 'tests.dat.vistrail_data':
                self.fail()
            return self.plot
        GlobalManager.get_plot = get_plot
        try:
            self.assertEqual(
                    VistrailData._read_recipe_annotation(
                            self.vistraildata,
                            'tests.dat.vistrail_data,My Plot'
                            ';param1=v='
                                'var1:1,2|'
                                'var2:5'
                            ';param2=c='
                                'test%27%22%3Bb%3Dc%2Cr%C3%A9mi:4'
                            ';param3=v='
                                'var3:3'),
                     (self.recipe, self.conn_map))
        finally:
            # Restore GlobalManager
            GlobalManager.get_plot = old_get_plot

    def test_build_portmap(self):
        """Tests the _build_annotation() method.
        """
        self.assertEqual(
                VistrailData._build_portmap_annotation(
                        self.port_map),
                'param1='
                    '1,port1:2,port2'
                ';param3='
                    '3,port3')
