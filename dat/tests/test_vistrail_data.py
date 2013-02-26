"""Tests for dat.vistrail_data.

"""


from itertools import count
import unittest

from dat.vistrail_data import VistrailData
from dat.tests import CallRecorder, FakeObj, odict


class Test_VistrailData(unittest.TestCase):
    def test_build_annotation_recipe(self):
        """Tests the _build_annotation_recipe() method.
        """
        recipe1 = FakeObj(
                plot=FakeObj(name='My Plot'),
                variables=odict(
                        ('param1', FakeObj(name='var1')),
                        ('param3', FakeObj(name='var2'))),
                constants=odict(
                        ('param2', 'test\'"'),
                        ('param4', 'a;b=c,d'),
                        ('param5', 'r\xC3\xA9mi'),
                        ))
        self.assertEqual(
                VistrailData._build_annotation_recipe(recipe1),
                'My Plot;'
                'param1=v:var1;'
                'param3=v:var2;'
                'param2=c:test%27%22;'
                'param4=c:a%3Bb%3Dc%2Cd;'
                'param5=c:r%C3%A9mi')

        recipe2 = FakeObj(
                plot=FakeObj(name='My Plot'),
                variables=dict(),
                constants=dict())
        self.assertEqual(
                VistrailData._build_annotation_recipe(recipe2),
                'My Plot')

    def test_read_annotation_recipe(self):
        """Tests the _read_annotation_recipe() method.
        """
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
                    'My Plot;'
                    'param1=v:var1;'
                    'param3=v:var2;'
                    'param2=c:test%27%22;'
                    'param4=c:a%3Bb%3Dc%2Cd;'
                    'param5=c:r%C3%A9mi')
            self.assertIs(recipe.plot, plot)
            self.assertEqual(
                    recipe.variables,
                    dict(param1=FakeVariable(1), param3=FakeVariable(2)))
            self.assertEqual(
                    get_variable.calls,
                    [(['var1'], dict()), (['var2'], dict())])
            self.assertEqual(
                    recipe.constants,
                    dict(
                            param2='test\'"',
                            param4='a;b=c,d',
                            param5='r\xC3\xA9mi'))
        finally:
            # Restore GlobalManager
            GlobalManager.get_plot = old_get_plot

    def test_build_annotation_portmap(self):
        """Tests the _build_annotation_portmap() method.
        """
        self.assertEqual(
                VistrailData._build_annotation_portmap(odict(
                        ('param1', [(1, 'port1'), (2, 'port2')]),
                        ('param2', []),
                        ('param3', [(3, 'port3')]))),
                'param1=1:port1,2:port2;param2=;param3=3:port3')

    def test_read_annotation_portmap(self):
        """Tests the _read_annotation_portmap() method.
        """
        self.assertEqual(
                VistrailData._read_annotation_portmap(
                        'param1=1:port1,2:port2;param2=;param3=3:port3'),
                dict(
                        param1=[(1, 'port1'), (2, 'port2')],
                        param2=[],
                        param3=[(3, 'port3')]))

    def test_build_annotation_varmap(self):
        """Tests the _build_annotation_varmap() method.
        """
        self.assertEqual(
                VistrailData._build_annotation_varmap(odict(
                        ('param1', [1, 2]),
                        ('param2', []),
                        ('param3', [3]))),
                'param1=1,2;param2=;param3=3')

    def test_read_annotation_varmap(self):
        """Tests the _read_annotation_varmap() method.
        """
        self.assertEqual(
                VistrailData._read_annotation_varmap(
                        'param1=1,2;param2=;param3=3'),
                dict(
                        param1=[1, 2],
                        param2=[],
                        param3=[3]))
