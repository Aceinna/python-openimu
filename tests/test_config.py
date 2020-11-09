import sys
import unittest

try:
    from aceinna.framework.configuration import (
        DEV_CONFIG, PROD_CONFIG, get_config)
except:
    sys.path.append('./src')
    from aceinna.framework.configuration import (
        DEV_CONFIG, PROD_CONFIG, get_config)


class TestConfig(unittest.TestCase):
    def test_get_dev_config(self):
        setattr(sys, '__dev__', True)
        config = get_config()
        self.assertEqual(config, DEV_CONFIG)

    def test_get_prod_config(self):
        delattr(sys, '__dev__')
        config = get_config()
        self.assertEqual(config, PROD_CONFIG)

    def test_get_prod_config_if_disable_dev(self):
        setattr(sys, '__dev__', False)
        config = get_config()
        self.assertEqual(config, PROD_CONFIG)


if __name__ == '__main__':
    unittest.main()
