"""Tests for variable name validation/correction.

"""


import unittest


class Test_variablenames(unittest.TestCase):
    def test_unique_varname(self):
        from dat.gui.load_variable_dialog import unique_varname

        class FakeData(object):
            def get_variable(self, varname):
                return None
        vistraildata = FakeData()

        self.assertEqual(
                unique_varname('variable', vistraildata),
                'variable (2)')
        self.assertEqual(
                unique_varname('variable (4)', vistraildata),
                'variable (5)')

    def test_validator(self):
        from dat.gui.load_variable_dialog import VariableNameValidator

        class FakeData(object):
            def get_variable(self, varname):
                return varname == 'existing' or None

        validator = VariableNameValidator(FakeData())

        self.assertTrue(validator.format('somename'))
        self.assertTrue(validator.unique('somename'))
        self.assertTrue(validator('somename'))

        self.assertTrue(validator.format('existing'))
        self.assertFalse(validator.unique('existing'))
        self.assertFalse(validator('existing'))

        self.assertFalse(validator.format(''))
        self.assertFalse(validator.format('some=name'))
        self.assertFalse(validator.format('some;name'))
        self.assertFalse(validator(''))
        self.assertFalse(validator('some=name'))
