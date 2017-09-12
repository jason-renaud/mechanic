from unittest import TestCase
from mechanic.mechanic.generator import Generator


class GeneratorTest(TestCase):
    def setUp(self):
        # self.generator = Generator("mech-petstore.json", "", "~/petstore", app_name="petstoretest")
        self.generator = Generator("mech-cmdb.json", "", "~/xyz", app_name="cmdb-xyz")

    def test_generate(self):
        self.generator.generate()

