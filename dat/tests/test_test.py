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
