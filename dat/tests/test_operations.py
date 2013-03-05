"""Tests for the operations (module dat.operations).

"""


import unittest

from dat.operations.execution import parent_modules, find_operation
from dat.operations.parsing import InvalidOperation, parse_expression, \
    SYMBOL, NUMBER, OP
import dat.tests

from vistrails.core.packagemanager import get_package_manager


class Test_operation_parsing(unittest.TestCase):
    def test_parser(self):
        """Tests the parse_expression function.
        """
        self.assertEqual(
                parse_expression('myvar= bb\t+ aa4b*2'),
                (
                    'myvar',
                    (OP, '+',
                        (SYMBOL, 'bb'),
                        (OP, '*',
                            (SYMBOL, 'aa4b'),
                            (NUMBER, 2)
                        )
                    )
                ))

        with self.assertRaises(InvalidOperation) as cm:
            parse_expression('t = a . b')
        self.assertIn("Error while parsing", cm.exception.message)

        with self.assertRaises(InvalidOperation) as cm:
            parse_expression('42 = 3 + 3')
        self.assertIn("Invalid target ", cm.exception.message)
        self.assertEqual(cm.exception.select, (0, 2)) # target selected

        with self.assertRaises(InvalidOperation) as cm:
            parse_expression('= 6*7')
        self.assertIn("Missing target ", cm.exception.message)
        self.assertEqual(cm.exception.fix, 'new_var = 6*7')
        self.assertEqual(cm.exception.select, (0, 7))

        with self.assertRaises(InvalidOperation) as cm:
            parse_expression('6*7')
        self.assertIn("Missing target ", cm.exception.message)
        self.assertEqual(cm.exception.fix, 'new_var = 6*7')
        self.assertEqual(cm.exception.select, (0, 7))

        self.assertEqual(parse_expression('a = 3 + 3')[0], 'a')

        self.assertEqual(
                parse_expression('b = 4 *cd(2+ 5, ac) + (1-4)/7'),
                (
                    'b',
                    (OP, '+',
                        (OP, '*',
                            (NUMBER, 4),
                            (OP, 'cd',
                                (OP, '+',
                                (NUMBER, 2),
                                (NUMBER, 5)
                                ),
                                (SYMBOL, 'ac'),
                             ),
                        ),
                        (OP, '/',
                            (OP, '-',
                                (NUMBER, 1),
                                (NUMBER, 4)
                            ),
                            (NUMBER, 7)
                        )
                    )
                ))

    @unittest.skip("Bug in tdparser, pending request")
    def test_invalid_parens(self):
        with self.assertRaises(InvalidOperation):
            parse_expression('new_var = 3 + (5*7')
        with self.assertRaises(InvalidOperation):
            parse_expression('new_var = 3 + 5*7)')
        with self.assertRaises(InvalidOperation):
            parse_expression('new_var = 3 + (5*)7')
        with self.assertRaises(InvalidOperation):
            parse_expression('new_var = 3 + 5(*7)')
        with self.assertRaises(InvalidOperation):
            parse_expression('new_var = 3 + 5(7)')


class Test_operations(unittest.TestCase):
    @classmethod
    def setUp(cls):
        cls._application = dat.tests.setup_application()
        if cls._application is None:
            raise unittest.SkipTest("No application is available")

        pm = get_package_manager()

        pm.late_enable_package(
                'pkg_test_operations',
                {'pkg_test_operations': 'dat.tests.'})

    def tearDown(self):
        pm = get_package_manager()
        pm.late_disable_package('pkg_test_operations')

    def test_parent_modules(self):
        import dat.tests.pkg_test_operations.init as pkg

        self.assertEqual(
                parent_modules(pkg.ModD),
                {pkg.ModD: 0, pkg.ModA: 1})
        self.assertEqual(
                parent_modules(pkg.ModE),
                {pkg.ModE: 0})
        self.assertEqual(
                parent_modules(pkg.ModC),
                {pkg.ModC: 0, pkg.ModB: 1, pkg.ModA: 2})

    def test_operation_resolution(self):
        import dat.tests.pkg_test_operations.init as pkg

        from vistrails.core.modules.basic_modules import Float, Integer
        from vistrails.packages.HTTP.init import HTTPFile

        self.assertIs(
                find_operation(
                        'overload_std',
                        [Float, HTTPFile]),
                pkg.overload_std_3)

        with self.assertRaises(InvalidOperation) as cm:
            find_operation(
                    'overload_std',
                    [Float, Integer])
        self.assertIn("Found no match", cm.exception.message)

        with self.assertRaises(InvalidOperation) as cm:
            find_operation('nonexistent', [])
        self.assertIn("There is no ", cm.exception.message)

        self.assertIs(
                find_operation(
                        'overload_custom',
                        [pkg.ModC, pkg.ModD]),
                pkg.overload_custom_2)

        with self.assertRaises(InvalidOperation) as cm:
            find_operation(
                    'overload_custom',
                    [pkg.ModE, pkg.ModE])

        self.assertIs(
                find_operation(
                        'overload_custom',
                        [pkg.ModD, pkg.ModD]),
                pkg.overload_custom_1)
