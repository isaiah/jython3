import unittest
from test import support

class MetaclassModuleTestCase(unittest.TestCase):
    def test_module_attribute(self):
        #Test for SF bug #1781500: wrong __module__ for classes with a metaclass
        from test_metaclass_support.simpleclass import TestClass
        self.assertTrue(TestClass.__module__.endswith('simpleclass'))

def test_main():
    support.run_unittest(MetaclassModuleTestCase)

if __name__ == '__main__':
    test_main()
