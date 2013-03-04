"""Tests for the operations (module dat.operations).

"""


import unittest

from dat.operations import InvalidExpression, parse_expression, \
    SYMBOL, NUMBER, OP


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

        with self.assertRaises(InvalidExpression) as cm:
            parse_expression('t = a . b')
        self.assertIn("Error while parsing", cm.exception.message)

        with self.assertRaises(InvalidExpression) as cm:
            parse_expression('42 = 3 + 3')
        self.assertIn("Invalid target ", cm.exception.message)
        self.assertEqual(cm.exception.select, (0, 2)) # target selected

        with self.assertRaises(InvalidExpression) as cm:
            parse_expression('= 6*7')
        self.assertIn("Missing target ", cm.exception.message)
        self.assertEqual(cm.exception.fix, 'new_var = 6*7')
        self.assertEqual(cm.exception.select, (0, 7))

        with self.assertRaises(InvalidExpression) as cm:
            parse_expression('6*7')
        self.assertIn("Missing target ", cm.exception.message)
        self.assertEqual(cm.exception.fix, 'new_var = 6*7')
        self.assertEqual(cm.exception.select, (0, 7))

        self.assertEqual(parse_expression('a = 3 + 3')[0], 'a')

        self.assertEqual(
                parse_expression('b = 4 *(2+ 5) + (1-4)/7'),
                (
                    'b',
                    (OP, '+',
                        (OP, '*',
                            (NUMBER, 4),
                            (OP, '+',
                                (NUMBER, 2),
                                (NUMBER, 5)
                            )
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
    def test_parens(self):
        with self.assertRaises(InvalidExpression):
            parse_expression('new_var = 3 + (5*7')
        with self.assertRaises(InvalidExpression):
            parse_expression('new_var = 3 + 5*7)')
        with self.assertRaises(InvalidExpression):
            parse_expression('new_var = 3 + (5*)7')
        with self.assertRaises(InvalidExpression):
            parse_expression('new_var = 3 + 5(*7)')
        with self.assertRaises(InvalidExpression):
            parse_expression('new_var = 3 + 5(7)')
