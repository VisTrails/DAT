"""Tests for the dat.utils module.

"""


import unittest
import warnings

from dat.tests import CallRecorder
from dat.utils import bisect, iswhitespace, catch_warning


class Test_utils(unittest.TestCase):
    def test_iswhitespace(self):
        self.assertTrue(iswhitespace('  \t\n'))
        self.assertTrue(iswhitespace(''))
        self.assertFalse(iswhitespace(' \ta  \n '))


class Test_bisect(unittest.TestCase):
    """Covers the bisect() function.
    """
    def test_simple(self):
        l = [1, 2, 3, 3, 7, 7, 9, 10]
        def getter(i):
            return l[i]

        self.assertEqual(bisect(8, getter, 0), 0)
        self.assertEqual(bisect(8, getter, 3), 4)
        self.assertEqual(bisect(8, getter, 5), 4)
        self.assertEqual(bisect(8, getter, 9), 7)
        self.assertEqual(bisect(8, getter, 12), 8)

    def test_raise(self):
        l = [1, 2, 3, 4, 5]
        self.assertRaises(ValueError, bisect,
                          5, lambda i: l[i], 6, -1)

    def test_reverse(self):
        def getter(i):
            return 100//i

        self.assertEqual(bisect(200, getter, 1, 1, lambda x, y: y<x),
                         101) # 100/100=1, 100/101=0
        self.assertEqual(bisect(200, getter, 3, 1, lambda x, y: y<x),
                         34) # 100/33=3, 100/34=2
        self.assertEqual(bisect(200, getter, 7, 1, lambda x, y: y<x),
                         15) # 100/14=7, 100/15=6
        self.assertEqual(bisect(200, getter, 11, 1, lambda x, y: y<x),
                         10) # 100/9=11, 100/10=10


class MyWarning(UserWarning):
    pass


class Test_catch_warning(unittest.TestCase):
    """Covers the catch_warning context manager.
    """
    def check_warnings(self, wlist, expected):
        self.assertEqual(
                [(w.category, w.message.message) for w in wlist],
                expected)

    def test_catches(self):
        h = CallRecorder()
        with warnings.catch_warnings(record=True) as toplevel:
            warnings.simplefilter('default')
            with catch_warning(MyWarning, record=True, handle=h) as caught:
                warnings.warn('one', category=UserWarning)
                warnings.warn('two', category=MyWarning)

        self.check_warnings(toplevel, [(UserWarning, 'one')])
        self.check_warnings(caught, [(MyWarning, 'two')])
        self.assertEqual(len(h.calls), 1)
        self.assertEqual(h.calls[0][0][0][0], 'two')
        self.assertEqual(h.calls[0][0][1], MyWarning)

    def test_ignore_filters(self):
        with warnings.catch_warnings(record=True) as toplevel:
            warnings.simplefilter('ignore')
            with catch_warning(MyWarning, record=True) as caught:
                warnings.warn('one', category=Warning)
                warnings.warn('two', category=MyWarning)

        self.check_warnings(toplevel, []) # filtered
        self.check_warnings(caught, [(MyWarning, 'two')])
