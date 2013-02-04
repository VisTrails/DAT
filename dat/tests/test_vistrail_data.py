"""Tests for dat.vistrail_data.

"""


from itertools import count
import unittest

from dat.vistrail_data import VistrailData
from dat.tests import CallRecorder, FakeObj, odict


class Test_VistrailData(unittest.TestCase):
    def test_build_annotation_recipe(self):
        recipe1 = FakeObj(
                plot=FakeObj(name='My Plot'),
                variables=odict(
                        ('param1', FakeObj(name='var1')),
                        ('param2', FakeObj(name='var2'))))
        self.assertEqual(
                VistrailData._build_annotation_recipe(recipe1),
                'My Plot;param1=var1;param2=var2')

        recipe2 = FakeObj(
                plot=FakeObj(name='My Plot'),
                variables=dict())
        self.assertEqual(
                VistrailData._build_annotation_recipe(recipe2),
                'My Plot')

    def test_read_annotation_recipe(self):
        from dat.global_data import GlobalManager

        class FakeVariable(object):
            def __init__(self, nb):
                self.name = nb
            def __eq__(self, other):
                return self.name == other.name

        plot = object()
        get_variable = CallRecorder(
                lambda name, c=count(1): FakeVariable(next(c)))
        vistraildata = FakeObj(get_variable=get_variable)

        # Patch GlobalManager
        old_get_plot = GlobalManager.get_plot
        GlobalManager.get_plot = CallRecorder(lambda name: plot)
        try:
            recipe = VistrailData._read_annotation_recipe(
                    vistraildata,
                    'My Plot;param1=var1;param2=var2')
            self.assertIs(recipe.plot, plot)
            self.assertEqual(
                    recipe.variables,
                    dict(param1=FakeVariable(1), param2=FakeVariable(2)))
            self.assertEqual(
                    get_variable.calls,
                    [(['var1'], dict()), (['var2'], dict())])
        finally:
            # Restore GlobalManager
            GlobalManager.get_plot = old_get_plot

    def test_build_annotation_portmap(self):
        self.assertEqual(
                VistrailData._build_annotation_portmap(odict(
                        ('param1', [(1, 'port1'), (2, 'port2')]),
                        ('param2', []),
                        ('param3', [(3, 'port3')]))),
                'param1=1:port1,2:port2;param2=;param3=3:port3')

    def test_read_annotation_portmap(self):
        self.assertEqual(
                VistrailData._read_annotation_portmap(
                        'param1=1:port1,2:port2;param2=;param3=3:port3'),
                dict(
                        param1=[(1, 'port1'), (2, 'port2')],
                        param2=[],
                        param3=[(3, 'port3')]))

    def test_build_annotation_varmap(self):
        self.assertEqual(
                VistrailData._build_annotation_varmap(odict(
                        ('param1', [1, 2]),
                        ('param2', []),
                        ('param3', [3]))),
                'param1=1,2;param2=;param3=3')

    def test_read_annotation_varmap(self):
        self.assertEqual(
                VistrailData._read_annotation_varmap(
                        'param1=1,2;param2=;param3=3'),
                dict(
                        param1=[1, 2],
                        param2=[],
                        param3=[3]))
