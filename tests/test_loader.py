import sys
import unittest

try:
    from aceinna.bootstrap.loader import (Loader, Webserver, CommandLine)
except:
    sys.path.append('./src')
    from aceinna.bootstrap.loader import (Loader, Webserver, CommandLine)


class TesLoader(unittest.TestCase):

    def test_create_webserver(self):
        instance = Loader.create('web', dict())
        self.assertTrue(isinstance(instance, Webserver))

    def test_create_cli(self):
        instance = Loader.create('cli', dict())
        self.assertTrue(isinstance(instance, CommandLine))

    def test_create_other(self):
        self.assertRaises(ValueError, Loader.create, 'other', dict())


if __name__ == '__main__':
    unittest.main()
