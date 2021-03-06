"""Tests for variable name validation/correction.

"""


import unittest


class Test_variablenames(unittest.TestCase):
    def test_unique_varname(self):
        """Tests the unique_varname() function.
        """
        from dat.gui.load_variable_dialog import unique_varname, \
            VariableNameValidator

        class FakeData(object):
            def get_variable(self, varname):
                if varname == 'variable_5':
                    return True
                else:
                    return None
        vistraildata = FakeData()

        new_varname = unique_varname('variable', vistraildata)
        self.assertEqual(
            new_varname,
            'variable_2')
        self.assertTrue(VariableNameValidator.format(new_varname))

        new_varname = unique_varname('variable_4', vistraildata)
        self.assertEqual(
            new_varname,
            'variable_6')
        self.assertTrue(VariableNameValidator.format(new_varname))

    def test_validator(self):
        """Tests the VariableNameValidator class.
        """
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

    def test_derive_varname(self):
        """Test the derive_varname() function.
        """
        from dat.packages import derive_varname
        from dat.gui.load_variable_dialog import VariableNameValidator

        tests = [
            (derive_varname('/usr/share/data/myfile.dat', remove_path=True),
             'myfile_dat'),
            (derive_varname('/usr/share/data/myfile.dat', remove_ext=True,
                            remove_path=True),
             'myfile'),
            (derive_varname('ma_donn\xE9e.dat', remove_ext=True,
                            prefix='a_', suffix='_b'),
             'a_ma_donn_e_b'),
            (derive_varname('another.name.test.data', remove_ext=True),
             'another_name_test'),
            (derive_varname('42', remove_ext=True),
             '_42'),
            (derive_varname('42', remove_ext=True, prefix='a'),
             'a42')
        ]
        for actual, expected in tests:
            self.assertEqual(actual, expected)
            self.assertTrue(VariableNameValidator.format(actual))
