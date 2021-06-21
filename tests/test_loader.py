import sys
import unittest

try:
    from aceinna.bootstrap.loader import (Loader, DefaultApp, CommandLineApp)
except:
    sys.path.append('./src')
    from aceinna.bootstrap.loader import (Loader, DefaultApp, CommandLineApp)


class TesLoader(unittest.TestCase):

    def test_create_webserver(self):
        instance = Loader.create('default', dict())
        self.assertTrue(isinstance(instance, DefaultApp))

    def test_create_cli(self):
        instance = Loader.create('cli', dict())
        self.assertTrue(isinstance(instance, CommandLineApp))

    def test_create_other(self):
        self.assertRaises(ValueError, Loader.create, 'other', dict())


if __name__ == '__main__':
    unittest.main()
