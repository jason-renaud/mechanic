from unittest import TestCase
from mechanic.mechanic.generator import Generator


class GeneratorTest(TestCase):
    def setUp(self):
        self.generator = Generator("mech-petstore.json", "~/petstore")

    def test_generate(self):
        self.generator.generate()

