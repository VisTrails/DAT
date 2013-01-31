"""Tests for the DAT tool.

"""


import unittest


class Test_startup(unittest.TestCase):
    def test_import_vistrails(self):
        """Imports VisTrails using 'import vistrails.xxx'
        """
        # Try importing
        import vistrails.core.modules.basic_modules
        # Verify that it was assigned
        self.assertIsNotNone(vistrails.core.modules.basic_modules.String)

    def test_import_vistrails_from(self):
        """Imports VisTrails using 'from vistrails.xxx ...'
        """
        # Try importing
        from vistrails.core.modules.basic_modules import String
        # Verify that it was assigned
        self.assertIsNotNone(String)

    def test_odict(self):
        from dat.tests import odict

        l1 = [(1, 2), (3, 4)]
        d1 = odict(*l1)
        self.assertEqual(d1.items(), l1)
        self.assertEqual(list(d1.iteritems()), l1)
        self.assertEqual(d1.keys(), [1, 3])
        self.assertEqual(list(d1.iterkeys()), [1, 3])
        self.assertEqual(d1.values(), [2, 4])
        self.assertEqual(list(d1.itervalues()), [2, 4])

        l2 = [(3, 4), (1, 2)]
        d2 = odict(*l2)
        self.assertEqual(d2.items(), l2)
        self.assertEqual(list(d2.iteritems()), l2)
        self.assertEqual(d2.keys(), [3, 1])
        self.assertEqual(list(d2.iterkeys()), [3, 1])
        self.assertEqual(d2.values(), [4, 2])
        self.assertEqual(list(d2.itervalues()), [4, 2])
