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
        with self.assertRaises(InvalidExpression):
            parse_expression('a . b')
        with self.assertRaises(InvalidExpression):
            parse_expression('2 = 3 + 3')
        self.assertEqual(parse_expression('a = 3 + 3')[0], 'a')
        self.assertEqual(
                parse_expression('4 *(2+ 5) + (1-4)/7'),
                (
                    None,
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
