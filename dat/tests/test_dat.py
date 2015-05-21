"""Tests for the dat package.

"""


import unittest

from dat import DATRecipe, RecipeParameterValue
from dat.tests import FakeObj


class TestRecipe(unittest.TestCase):
    def test_eq(self):
        myvar = FakeObj(name='myvar')
        othervar = FakeObj(name='othervar')
        plot = FakeObj(package_identifier='tests.dat', name='My Plot')
        plot2 = FakeObj(package_identifier='tests.dat', name='Not My Plot')
        rec1 = DATRecipe(
                plot,
                dict(
                        param1=[],
                        param2=[RecipeParameterValue(variable=myvar)]))
        rec2 = DATRecipe(
                plot2,
                dict(
                        param1=[],
                        param2=[RecipeParameterValue(variable=myvar)]))
        rec3 = DATRecipe(
                plot,
                dict(
                        param1=(),
                        param2=(RecipeParameterValue(variable=myvar),)))
        rec4 = DATRecipe(
                plot,
                dict(
                        param1=[RecipeParameterValue(variable=othervar)],
                        param2=[RecipeParameterValue(variable=myvar)]))
        rec5 = DATRecipe(
                plot,
                dict(
                        param1=[],
                        param2=[RecipeParameterValue(constant='myvar')]))
        rec6 = DATRecipe(
                plot,
                dict(
                        param1=[],
                        param2=[RecipeParameterValue(constant='othervar')]))
        rec7 = DATRecipe(
                plot,
                dict(
                        param1=[],
                        param2=[RecipeParameterValue(variable=myvar,
                                                     typecast='op1')]))
        rec8 = DATRecipe(
                plot,
                dict(
                        param1=[],
                        param2=[RecipeParameterValue(variable=myvar,
                                                     typecast='*')]))

        self.assertTrue(rec1 == rec1)
        self.assertTrue(rec3 == rec3)
        self.assertTrue(rec5 == rec5)
        self.assertFalse(rec1 == rec2)
        self.assertTrue(rec1 == rec3)
        self.assertFalse(rec1 == rec4)
        self.assertFalse(rec1 == rec5)
        self.assertFalse(rec1 == rec6)
        self.assertTrue(rec1 == rec7)
        self.assertTrue(rec7 == rec7)
        self.assertTrue(rec7 == rec8)
