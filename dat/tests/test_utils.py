"""Tests for the dat.utils module.

"""


import unittest

from dat.utils import bisect, iswhitespace


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

    def test_iswhitespace(self):
        self.assertTrue(iswhitespace('  \t\n'))
        self.assertTrue(iswhitespace(''))
        self.assertFalse(iswhitespace(' \ta  \n '))
